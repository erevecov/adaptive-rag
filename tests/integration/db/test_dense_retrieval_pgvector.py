"""Integracion de dense retrieval exacto contra Postgres + pgvector."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from sqlalchemy import Engine

from adaptive_rag.db.models import EMBEDDING_DIMENSIONS
from adaptive_rag.db.repositories import (
    ChunkRepository,
    DocumentRepository,
    ProjectRepository,
    SourceRepository,
)
from adaptive_rag.db.session import create_session_factory
from adaptive_rag.retrieval import DenseRetriever

REPO_ROOT = Path(__file__).resolve().parents[3]


def run_alembic_upgrade(database_url: str) -> None:
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


def _vector(first: float) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = first
    return values


def test_dense_retriever_orders_by_pgvector_l2_distance(
    pg_url: str,
    pg_engine: Engine,
) -> None:
    run_alembic_upgrade(pg_url)
    session = create_session_factory(pg_engine)()
    try:
        project = ProjectRepository(session).create(name="pgvector-retrieval")
        source = SourceRepository(session).create(
            project_id=project.id,
            source_type="markdown",
            external_id="guide.md",
        )
        document = DocumentRepository(session).create_document(
            project_id=project.id,
            source_id=source.id,
            stable_id="guide.md",
        )
        version = DocumentRepository(session).create_version(
            project_id=project.id,
            document_id=document.id,
            version_number=1,
            normalized_text="Near evidence\n\nFar evidence",
            content_hash="sha256:pgvector",
            index_fingerprint="fp:pgvector",
        )
        far = ChunkRepository(session).create(
            project_id=project.id,
            document_version_id=version.id,
            ordinal=1,
            char_start=15,
            char_end=27,
            embedding=_vector(0.9),
        )
        near = ChunkRepository(session).create(
            project_id=project.id,
            document_version_id=version.id,
            ordinal=0,
            char_start=0,
            char_end=13,
            embedding=_vector(0.1),
        )
        session.commit()

        results = DenseRetriever(session).search(
            project_id=project.id,
            query_embedding=_vector(0.0),
            limit=2,
        )

        assert [result.chunk_id for result in results] == [near.id, far.id]
        assert [result.citation.snippet for result in results] == [
            "Near evidence",
            "Far evidence",
        ]
    finally:
        session.close()
