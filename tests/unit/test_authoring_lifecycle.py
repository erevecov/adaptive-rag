"""M43 authoring lifecycle and index cascade."""

from __future__ import annotations

from sqlalchemy import func, select

from adaptive_rag import authoring
from adaptive_rag.chunking import ChunkingPipeline
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Chunk,
    ChunkSparseEmbedding,
    Document,
    DocumentVersion,
    Project,
    Source,
)
from adaptive_rag.db.repositories import DocumentRepository, ProjectRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.embeddings import (
    DenseEmbeddingPipeline,
    FakeDenseEmbeddingProvider,
    FakeSparseEmbeddingProvider,
    SparseEmbeddingPipeline,
)


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


def test_update_and_soft_delete_project() -> None:
    session = _make_session()
    project = authoring.create_project(session, name="Alpha")
    updated = authoring.update_project(session, project.id, name="Beta")
    assert updated.name == "Beta"
    deleted = authoring.soft_delete_project(session, project.id)
    assert deleted.deleted_at is not None
    assert ProjectRepository(session).get(project.id) is None
    assert authoring.list_projects(session) == []


def test_soft_delete_source_cascades_index_rows() -> None:
    session = _make_session()
    project = authoring.create_project(session, name="Demo")
    source = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id="notes.md",
        extra_metadata={"content": "# Notes\n\nIndex cascade evidence."},
    )
    document = DocumentRepository(session).create_document(
        project_id=project.id,
        source_id=source.id,
        stable_id=source.external_id,
    )
    version = DocumentRepository(session).create_version(
        project_id=project.id,
        document_id=document.id,
        version_number=1,
        normalized_text="# Notes\n\nIndex cascade evidence.",
        content_hash="sha256:x",
        index_fingerprint="sha256:y",
        parser_metadata={},
        extraction_metadata={},
    )
    ChunkingPipeline(session).chunk_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    DenseEmbeddingPipeline(
        session, provider=FakeDenseEmbeddingProvider()
    ).embed_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    SparseEmbeddingPipeline(
        session, provider=FakeSparseEmbeddingProvider()
    ).embed_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    assert session.scalar(select(func.count()).select_from(Chunk)) >= 1

    deleted = authoring.soft_delete_source(
        session,
        project_id=project.id,
        source_id=source.id,
    )
    assert deleted.deleted_at is not None
    assert session.scalar(select(func.count()).select_from(Chunk)) == 0
    assert session.scalar(select(func.count()).select_from(Document)) == 0
    assert session.scalar(select(func.count()).select_from(DocumentVersion)) == 0
