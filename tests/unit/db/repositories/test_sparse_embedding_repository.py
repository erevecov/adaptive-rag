"""Tests for sparse embedding repository helpers."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Chunk,
    ChunkSparseEmbedding,
    Document,
    DocumentVersion,
    Project,
    Source,
)
from adaptive_rag.db.repositories import (
    ChunkRepository,
    DocumentRepository,
    ProjectRepository,
    SourceRepository,
    SparseEmbeddingRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.embeddings import SparseEmbeddingVector


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
            ChunkSparseEmbedding.__table__,
        ],
    )
    return create_session_factory(engine)()


def _create_chunk(session, *, project: Project | None = None) -> tuple[Project, Chunk]:
    active_project = project or ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=active_project.id,
        source_type="markdown",
        external_id="guide.md",
    )
    document = DocumentRepository(session).create_document(
        project_id=active_project.id,
        source_id=source.id,
        stable_id="guide.md",
    )
    version = DocumentRepository(session).create_version(
        project_id=active_project.id,
        document_id=document.id,
        version_number=1,
        normalized_text="Alpha sparse evidence",
        content_hash="sha256:test",
        index_fingerprint="ingestion-fp",
    )
    chunk = ChunkRepository(session).create(
        project_id=active_project.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=0,
        char_end=len(version.normalized_text),
    )
    session.flush()
    return active_project, chunk


def test_sparse_embedding_repository_upserts_current_row_and_replaces_stale() -> None:
    session = _make_session()
    project, chunk = _create_chunk(session)
    stale = ChunkSparseEmbedding(
        chunk_id=chunk.id,
        sparse_indices=[99],
        sparse_values=[0.1],
        sparse_tokens=["stale"],
        sparse_size=1,
        input_hash="sha256:stale",
        index_fingerprint="fp-stale",
    )
    session.add(stale)
    session.commit()

    row = SparseEmbeddingRepository(session).upsert_current(
        project_id=project.id,
        chunk_id=chunk.id,
        vector=SparseEmbeddingVector(
            indices=(3, 7),
            values=(0.25, 0.75),
            tokens=("alpha", "sparse"),
        ),
        input_hash="sha256:current",
        index_fingerprint="fp-current",
        extra_metadata={"provider": "fake"},
    )
    session.commit()

    rows = session.scalars(select(ChunkSparseEmbedding)).all()
    assert [stored.id for stored in rows] == [row.id]
    assert rows[0].sparse_indices == [3, 7]
    assert rows[0].sparse_values == [0.25, 0.75]
    assert rows[0].sparse_tokens == ["alpha", "sparse"]
    assert rows[0].sparse_size == 2
    assert rows[0].input_hash == "sha256:current"
    assert rows[0].index_fingerprint == "fp-current"
    assert rows[0].extra_metadata == {"provider": "fake"}


def test_sparse_embedding_repository_rejects_cross_project_chunk() -> None:
    session = _make_session()
    _project, chunk = _create_chunk(session)
    other_project = ProjectRepository(session).create(name="other")
    session.commit()

    with pytest.raises(ValueError, match="chunk does not belong to project"):
        SparseEmbeddingRepository(session).upsert_current(
            project_id=other_project.id,
            chunk_id=chunk.id,
            vector=SparseEmbeddingVector(indices=(1,), values=(1.0,)),
            input_hash="sha256:input",
            index_fingerprint="fp-current",
        )
