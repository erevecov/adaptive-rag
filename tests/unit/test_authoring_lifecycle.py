"""M43 authoring lifecycle and index cascade."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, func, select

from adaptive_rag import authoring
from adaptive_rag.chunking import ChunkingPipeline
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    ChatSession,
    Chunk,
    ChunkSparseEmbedding,
    Document,
    DocumentVersion,
    Project,
    RetrievalRun,
    RetrievedChunk,
    Source,
    ToolCall,
    User,
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


def test_soft_delete_source_preserves_citation_audit_rows() -> None:
    """Chunks cited by past retrieval runs must not block the cascade (M43)."""

    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_conn, _):  # type: ignore[no-untyped-def]
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
            ChunkSparseEmbedding.__table__,
            User.__table__,
            ChatSession.__table__,
            ToolCall.__table__,
            RetrievalRun.__table__,
            RetrievedChunk.__table__,
        ],
    )
    session = create_session_factory(engine)()
    project = authoring.create_project(session, name="Demo")
    source = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id="notes.md",
        extra_metadata={"content": "# Notes\n\nCited content."},
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
        normalized_text="# Notes\n\nCited content.",
        content_hash="sha256:x",
        index_fingerprint="sha256:y",
        parser_metadata={},
        extraction_metadata={},
    )
    ChunkingPipeline(session).chunk_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    chunk_id = session.scalar(select(Chunk.id))
    assert chunk_id is not None

    chat_session = ChatSession(
        id=uuid4(), project_id=project.id, status="succeeded"
    )
    session.add(chat_session)
    session.flush()
    run = RetrievalRun(
        id=uuid4(),
        project_id=project.id,
        session_id=chat_session.id,
        query="cited?",
        strategy="dense",
        top_k=5,
    )
    session.add(run)
    session.flush()
    retrieved = RetrievedChunk(
        id=uuid4(),
        project_id=project.id,
        retrieval_run_id=run.id,
        chunk_id=chunk_id,
        rank=1,
        citation_json={"chunk_id": str(chunk_id), "snippet": "Cited content."},
    )
    session.add(retrieved)
    session.commit()

    authoring.soft_delete_source(
        session,
        project_id=project.id,
        source_id=source.id,
    )
    session.commit()

    assert session.scalar(select(func.count()).select_from(Chunk)) == 0
    # Citation audit row survives with the chunk reference nulled.
    session.expire_all()
    persisted = session.get(RetrievedChunk, retrieved.id)
    assert persisted is not None
    assert persisted.chunk_id is None
    assert persisted.citation_json["snippet"] == "Cited content."


def test_recreate_source_after_soft_delete_restores_identity() -> None:
    session = _make_session()
    project = authoring.create_project(session, name="Demo")
    source = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id="notes.md",
        extra_metadata={"content": "# Notes"},
    )
    authoring.soft_delete_source(
        session,
        project_id=project.id,
        source_id=source.id,
    )

    recreated = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id="notes.md",
        tags=["v2"],
        extra_metadata={"content": "# Notes v2"},
    )
    assert recreated.id == source.id
    assert recreated.deleted_at is None
    assert recreated.tags == ["v2"]
    assert recreated.extra_metadata == {"content": "# Notes v2"}


def test_update_source_external_id_conflict_returns_409() -> None:
    session = _make_session()
    project = authoring.create_project(session, name="Demo")
    authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id="a.md",
        extra_metadata={"content": "# A"},
    )
    source_b = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id="b.md",
        extra_metadata={"content": "# B"},
    )

    with pytest.raises(authoring.AuthoringError) as excinfo:
        authoring.update_source(
            session,
            project_id=project.id,
            source_id=source_b.id,
            external_id="a.md",
        )
    assert excinfo.value.status_code == 409
