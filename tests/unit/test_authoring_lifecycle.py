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


def test_create_source_revives_soft_deleted_identity() -> None:
    session = _make_session()
    project = authoring.create_project(session, name="Revive")
    first = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id="notes.md",
        tags=["v1"],
        extra_metadata={"content": "# v1"},
    )
    authoring.soft_delete_source(
        session, project_id=project.id, source_id=first.id
    )
    revived = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id="notes.md",
        tags=["v2"],
        extra_metadata={"content": "# v2 revived"},
    )
    assert revived.id == first.id
    assert revived.deleted_at is None
    assert revived.tags == ["v2"]
    assert revived.extra_metadata == {"content": "# v2 revived"}


def test_soft_delete_source_preserves_retrieved_chunk_rows() -> None:
    """Deleting index chunks must not fail when past retrieval cited them."""

    # Import models package so all FK-related tables register on Base.metadata.
    import adaptive_rag.db.models  # noqa: F401
    from adaptive_rag.db.models import (
        ChatSession,
        RetrievalRun,
        RetrievedChunk,
    )

    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()
    project = authoring.create_project(session, name="Cite")
    source = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id="cited.md",
        extra_metadata={"content": "# Cited\n\nBody."},
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
        normalized_text="# Cited\n\nBody.",
        content_hash="sha256:c",
        index_fingerprint="sha256:d",
        parser_metadata={},
        extraction_metadata={},
    )
    ChunkingPipeline(session).chunk_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    chunk = session.scalars(select(Chunk)).first()
    assert chunk is not None
    chat = ChatSession(
        project_id=project.id,
        status="succeeded",
        model_config_json={},
        prompt_version="t",
    )
    session.add(chat)
    session.flush()
    run = RetrievalRun(
        project_id=project.id,
        session_id=chat.id,
        query="q",
        strategy="dense",
        top_k=5,
    )
    session.add(run)
    session.flush()
    session.add(
        RetrievedChunk(
            project_id=project.id,
            retrieval_run_id=run.id,
            chunk_id=chunk.id,
            rank=1,
            citation_json={"snippet": "Body."},
        )
    )
    session.flush()

    authoring.soft_delete_source(
        session, project_id=project.id, source_id=source.id
    )
    session.expire_all()
    remaining = session.scalars(select(RetrievedChunk)).all()
    assert len(remaining) == 1
    assert remaining[0].chunk_id is None
    assert remaining[0].citation_json["snippet"] == "Body."
