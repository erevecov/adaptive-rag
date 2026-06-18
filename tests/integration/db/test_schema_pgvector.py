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


def run_alembic_upgrade(database_url: str) -> None:
    """Aplica `alembic upgrade head` via `uv run` con la URL dada."""
    env = {**os.environ, "ADAPTIVE_RAG_DATABASE_URL": database_url}
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
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


def vector_literal(dimensions: int) -> str:
    inner = ",".join(["0"] * dimensions)
    return f"[{inner}]"


def test_alembic_upgrade_applies_cleanly(pg_url: str, pg_engine: Engine) -> None:
    run_alembic_upgrade(pg_url)

    inspector = inspect(pg_engine)
    table_names = set(inspector.get_table_names())

    for expected in (
        "projects",
        "sources",
        "documents",
        "document_versions",
        "chunks",
        "chunk_sparse_embeddings",
    ):
        assert expected in table_names, expected


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
        project_id = "00000000-0000-0000-0000-000000000002"
        source_id = "00000000-0000-0000-0000-000000000003"
        document_id = "00000000-0000-0000-0000-000000000004"
        version_id = "00000000-0000-0000-0000-000000000005"
        conn.execute(
            text(
                "INSERT INTO projects (id, name) VALUES (:id, 'dim-test')"
            ),
            {"id": project_id},
        )
        conn.execute(
            text(
                "INSERT INTO sources (id, project_id, source_type, external_id) "
                "VALUES (:id, :pid, 'web', 'ext')"
            ),
            {"id": source_id, "pid": project_id},
        )
        conn.execute(
            text(
                "INSERT INTO documents (id, project_id, source_id, stable_id) "
                "VALUES (:id, :pid, :sid, 'stable')"
            ),
            {"id": document_id, "pid": project_id, "sid": source_id},
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

    assert "project_id" in indexed_columns("sources")
    assert "project_id" in indexed_columns("documents")
    assert "source_id" in indexed_columns("documents")
    assert "document_id" in indexed_columns("document_versions")
    assert "document_version_id" in indexed_columns("chunks")
    assert "chunk_id" in indexed_columns("chunk_sparse_embeddings")
