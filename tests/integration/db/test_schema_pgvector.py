"""Tests de integracion del schema de dominio contra Postgres + pgvector.

Validan que:
- `alembic upgrade head` aplica sin error sobre un schema limpio.
- `chunks.embedding` es una columna `vector(1024)`.
- Las columnas de aislamiento y filtering estan indexadas.

Requieren Docker corriendo (testcontainers).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from uuid import uuid4

import psycopg.errors
import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import DataError, IntegrityError, StatementError

# Errores que indican que Postgres rechazo el vector por dimension.
DB_ERROR = (
    DataError,
    IntegrityError,
    StatementError,
    psycopg.errors.DataError,
    psycopg.errors.InternalError_,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def run_alembic_upgrade(database_url: str, target: str = "head") -> None:
    """Aplica `alembic upgrade <target>` via `uv run` con la URL dada."""
    env = {**os.environ, "ADAPTIVE_RAG_DATABASE_URL": database_url}
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", target],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"alembic upgrade head failed (rc={result.returncode}).\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )


def test_job_platform_migration_backfills_existing_jobs(
    pg_url: str, pg_engine: Engine
) -> None:
    run_alembic_upgrade(pg_url, target="n4o5p6q7r8s9")
    workspace_id = uuid4()
    job_id = uuid4()
    with pg_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO workspaces (id, name) VALUES (:id, 'legacy-jobs')"),
            {"id": workspace_id},
        )
        connection.execute(
            text(
                "INSERT INTO jobs "
                "(id, workspace_id, job_type, status, payload_json, attempts, "
                "max_attempts) VALUES "
                "(:id, :workspace_id, 'ingest_source', 'queued', "
                "CAST('{}' AS jsonb), 2, 3)"
            ),
            {"id": job_id, "workspace_id": workspace_id},
        )

    run_alembic_upgrade(pg_url)

    with pg_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT id, scope, queue_name, handler_version, attempt_count, "
                "retry_count, max_retries FROM jobs WHERE id=:id"
            ),
            {"id": job_id},
        ).mappings().one()
        queue_names = set(
            connection.execute(text("SELECT name FROM job_queues")).scalars()
        )

    assert dict(row) == {
        "id": job_id,
        "scope": "workspace",
        "queue_name": "ingestion",
        "handler_version": 1,
        "attempt_count": 2,
        "retry_count": 2,
        "max_retries": 2,
    }
    assert queue_names == {"default", "ingestion", "system"}


def vector_literal(dimensions: int) -> str:
    inner = ",".join(["0"] * dimensions)
    return f"[{inner}]"


def test_alembic_upgrade_applies_cleanly(pg_url: str, pg_engine: Engine) -> None:
    run_alembic_upgrade(pg_url)

    inspector = inspect(pg_engine)
    table_names = set(inspector.get_table_names())

    for expected in (
        "workspaces",
        "sources",
        "documents",
        "document_versions",
        "chunks",
        "chunk_sparse_embeddings",
        "jobs",
        "job_events",
    ):
        assert expected in table_names, expected

    workspace_columns = {c["name"] for c in inspector.get_columns("workspaces")}
    assert "budget_config_json" in workspace_columns
    assert "budget_config" not in workspace_columns


def test_chunks_embedding_is_vector_type(pg_url: str, pg_engine: Engine) -> None:
    run_alembic_upgrade(pg_url)

    with pg_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT data_type, udt_name "
                "FROM information_schema.columns "
                "WHERE table_name = 'chunks' AND column_name = 'embedding'"
            )
        ).one()

    # pgvector expone la columna como USER-DEFINED con udt_name 'vector'.
    assert row.data_type == "USER-DEFINED"
    assert row.udt_name == "vector"

    chunk_columns = {c["name"] for c in inspect(pg_engine).get_columns("chunks")}
    assert "embedding_metadata" in chunk_columns


def test_vector_1024_dimensions_accepted(pg_url: str, pg_engine: Engine) -> None:
    run_alembic_upgrade(pg_url)

    # CAST evita que el '::vector' colisione con el placeholder ':v' de
    # SQLAlchemy text().
    with pg_engine.begin() as conn:
        conn.execute(text("SELECT CAST(:v AS vector)"), {"v": vector_literal(1024)})


def test_chunk_column_rejects_wrong_embedding_dimension(
    pg_url: str, pg_engine: Engine
) -> None:
    """La columna chunks.embedding es vector(1024): un vector de 1023 dims
    debe ser rechazado al insertar, validando el constraint de dimension."""
    run_alembic_upgrade(pg_url)

    with pg_engine.begin() as conn:
        workspace_id = "00000000-0000-0000-0000-000000000002"
        source_id = "00000000-0000-0000-0000-000000000003"
        document_id = "00000000-0000-0000-0000-000000000004"
        version_id = "00000000-0000-0000-0000-000000000005"
        conn.execute(
            text(
                "INSERT INTO workspaces (id, name) VALUES (:id, 'dim-test')"
            ),
            {"id": workspace_id},
        )
        conn.execute(
            text(
                "INSERT INTO sources (id, workspace_id, source_type, external_id) "
                "VALUES (:id, :pid, 'web', 'ext')"
            ),
            {"id": source_id, "pid": workspace_id},
        )
        conn.execute(
            text(
                "INSERT INTO documents (id, workspace_id, source_id, stable_id) "
                "VALUES (:id, :pid, :sid, 'stable')"
            ),
            {"id": document_id, "pid": workspace_id, "sid": source_id},
        )
        conn.execute(
            text(
                "INSERT INTO document_versions "
                "(id, document_id, version_number, normalized_text, "
                "content_hash, index_fingerprint) "
                "VALUES (:id, :did, 1, 'x', 'h', 'fp')"
            ),
            {"id": version_id, "did": document_id},
        )
        # Un embedding de 1024 dims debe aceptarse.
        conn.execute(
            text(
                "INSERT INTO chunks (id, document_version_id, ordinal, "
                "char_start, char_end, embedding) "
                "VALUES (:id, :vid, 0, 0, 1, CAST(:emb AS vector))"
            ),
            {
                "id": "00000000-0000-0000-0000-000000000006",
                "vid": version_id,
                "emb": vector_literal(1024),
            },
        )

    # Un embedding de 1023 dims debe ser rechazado por la columna vector(1024).
    with pg_engine.begin() as conn:
        with pytest.raises(DB_ERROR):
            conn.execute(
                text(
                    "INSERT INTO chunks (id, document_version_id, ordinal, "
                    "char_start, char_end, embedding) "
                    "VALUES (:id, :vid, 1, 0, 1, CAST(:emb AS vector))"
                ),
                {
                    "id": "00000000-0000-0000-0000-000000000007",
                    "vid": version_id,
                    "emb": vector_literal(1023),
                },
            )


def test_isolation_and_filtering_columns_are_indexed(
    pg_url: str, pg_engine: Engine
) -> None:
    run_alembic_upgrade(pg_url)

    inspector = inspect(pg_engine)

    def indexed_columns(table_name: str) -> set[str]:
        cols: set[str] = set()
        for idx in inspector.get_indexes(table_name):
            cols.update(idx["column_names"] or [])
        pk = inspector.get_pk_constraint(table_name)
        cols.update(pk.get("constrained_columns") or [])
        return cols

    assert "workspace_id" in indexed_columns("sources")
    assert "source_type" in indexed_columns("sources")
    assert "created_at" in indexed_columns("sources")
    assert "tags" in indexed_columns("sources")
    assert "workspace_id" in indexed_columns("documents")
    assert "source_id" in indexed_columns("documents")
    assert "document_id" in indexed_columns("document_versions")
    assert "document_version_id" in indexed_columns("chunks")
    assert "chunk_id" in indexed_columns("chunk_sparse_embeddings")
    assert "sparse_indices" in indexed_columns("chunk_sparse_embeddings")
    assert "workspace_id" in indexed_columns("jobs")
    assert "status" in indexed_columns("jobs")
    assert "run_after" in indexed_columns("jobs")
    assert "priority" in indexed_columns("jobs")
    assert "locked_until" in indexed_columns("jobs")
    assert "job_id" in indexed_columns("job_events")
    assert "event_type" in indexed_columns("job_events")


def test_identity_and_range_constraints_are_enforced(
    pg_url: str, pg_engine: Engine
) -> None:
    run_alembic_upgrade(pg_url)

    workspace_id = "00000000-0000-0000-0000-000000000102"
    source_id = "00000000-0000-0000-0000-000000000103"
    document_id = "00000000-0000-0000-0000-000000000104"
    version_id = "00000000-0000-0000-0000-000000000105"
    chunk_id = "00000000-0000-0000-0000-000000000106"

    with pg_engine.begin() as conn:
        conn.execute(
            text("INSERT INTO workspaces (id, name) VALUES (:id, 'constraint-test')"),
            {"id": workspace_id},
        )
        conn.execute(
            text(
                "INSERT INTO sources (id, workspace_id, source_type, external_id) "
                "VALUES (:id, :pid, 'web', 'ext')"
            ),
            {"id": source_id, "pid": workspace_id},
        )
        conn.execute(
            text(
                "INSERT INTO documents (id, workspace_id, source_id, stable_id) "
                "VALUES (:id, :pid, :sid, 'stable')"
            ),
            {"id": document_id, "pid": workspace_id, "sid": source_id},
        )
        conn.execute(
            text(
                "INSERT INTO document_versions "
                "(id, document_id, version_number, normalized_text, "
                "content_hash, index_fingerprint) "
                "VALUES (:id, :did, 1, 'x', 'h', 'fp')"
            ),
            {"id": version_id, "did": document_id},
        )
        conn.execute(
            text(
                "INSERT INTO chunks (id, document_version_id, ordinal, "
                "char_start, char_end) VALUES (:id, :vid, 0, 0, 1)"
            ),
            {"id": chunk_id, "vid": version_id},
        )

    invalid_statements = [
        (
            "INSERT INTO workspaces (id, name, embedding_mode) VALUES "
            "('00000000-0000-0000-0000-000000000112', 'bad-mode', 'bogus')",
            {},
        ),
        (
            "INSERT INTO sources (id, workspace_id, source_type, external_id) "
            "VALUES ('00000000-0000-0000-0000-000000000107', :pid, 'web', 'ext')",
            {"pid": workspace_id},
        ),
        (
            "INSERT INTO documents (id, workspace_id, source_id, stable_id) "
            "VALUES ('00000000-0000-0000-0000-000000000108', :pid, :sid, "
            "'stable')",
            {"pid": workspace_id, "sid": source_id},
        ),
        (
            "INSERT INTO document_versions "
            "(id, document_id, version_number, normalized_text, content_hash, "
            "index_fingerprint) VALUES "
            "('00000000-0000-0000-0000-000000000109', :did, 0, 'x', 'h2', 'fp2')",
            {"did": document_id},
        ),
        (
            "INSERT INTO chunks (id, document_version_id, ordinal, char_start, "
            "char_end) VALUES "
            "('00000000-0000-0000-0000-000000000110', :vid, 1, 5, 5)",
            {"vid": version_id},
        ),
        (
            "INSERT INTO chunks (id, document_version_id, ordinal, char_start, "
            "char_end) VALUES "
            "('00000000-0000-0000-0000-000000000113', :vid, -1, 0, 1)",
            {"vid": version_id},
        ),
        (
            "INSERT INTO chunk_sparse_embeddings "
            "(id, chunk_id, sparse_indices, sparse_values, sparse_size, "
            "input_hash, index_fingerprint) VALUES "
            "('00000000-0000-0000-0000-000000000111', :cid, "
            "CAST('[0]' AS jsonb), CAST('[1.0]' AS jsonb), -1, 'ih', "
            "'fp-sparse')",
            {"cid": chunk_id},
        ),
    ]

    for statement, params in invalid_statements:
        with pytest.raises(DB_ERROR):
            with pg_engine.begin() as conn:
                conn.execute(text(statement), params)
