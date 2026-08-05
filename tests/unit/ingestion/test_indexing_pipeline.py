"""Tests for public index_document_version jobs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Chunk,
    ChunkSparseEmbedding,
    Document,
    DocumentVersion,
    Job,
    JobEvent,
    Project,
    Source,
)
from adaptive_rag.db.repositories import (
    DocumentRepository,
    JobRepository,
    ProjectRepository,
    SourceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.embeddings import (
    FakeDenseEmbeddingProvider,
    FakeSparseEmbeddingProvider,
)
from adaptive_rag.ingestion.indexing import (
    INDEX_DOCUMENT_VERSION_JOB_TYPE,
    IndexingBlockedResult,
    IndexingPipeline,
)
from adaptive_rag.ingestion.pipeline import INGEST_SOURCE_JOB_TYPE, IngestionPipeline


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
            Job.__table__,
            JobEvent.__table__,
        ],
    )
    return create_session_factory(engine)()


def _run_time() -> datetime:
    return datetime(2026, 8, 5, 12, 0, tzinfo=UTC)


def test_successful_ingest_enqueues_index_job_without_creating_chunks() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="notes.md",
        extra_metadata={"content": "# Title\n\nBody evidence for indexing."},
    )
    JobRepository(session).create(
        project_id=project.id,
        job_type=INGEST_SOURCE_JOB_TYPE,
        payload_json={"source_id": str(source.id)},
        run_after=_run_time(),
    )
    session.commit()

    result = IngestionPipeline(session).run_next(
        project_id=project.id,
        worker_id="worker-1",
        now=_run_time(),
        lease_until=_run_time() + timedelta(minutes=5),
    )

    assert result is not None
    assert result.created_document_version is True
    assert session.scalar(select(func.count()).select_from(Chunk)) == 0

    index_jobs = JobRepository(session).list(
        project_id=project.id,
        job_type=INDEX_DOCUMENT_VERSION_JOB_TYPE,
    )
    assert len(index_jobs) == 1
    assert index_jobs[0].status == "queued"
    assert index_jobs[0].payload_json == {
        "document_version_id": str(result.document_version.id),
        "source_id": str(source.id),
    }


def test_index_job_creates_chunks_contextual_summaries_and_embeddings() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="notes.md",
        extra_metadata={
            "content": (
                "# Adaptive indexing\n\n"
                "Public indexing jobs prove chunks and embeddings exist."
            )
        },
    )
    JobRepository(session).create(
        project_id=project.id,
        job_type=INGEST_SOURCE_JOB_TYPE,
        payload_json={"source_id": str(source.id)},
        run_after=_run_time(),
    )
    session.commit()

    IngestionPipeline(session).run_next(
        project_id=project.id,
        worker_id="worker-1",
        now=_run_time(),
        lease_until=_run_time() + timedelta(minutes=5),
    )

    dense = FakeDenseEmbeddingProvider()
    sparse = FakeSparseEmbeddingProvider()
    # Index job is enqueued with wall-clock run_after; lease clock must not
    # be earlier than that value (fixed _run_time() can lag wall clock).
    index_now = datetime.now(UTC)
    result = IndexingPipeline(
        session,
        dense_embedding_provider=dense,
        sparse_embedding_provider=sparse,
    ).run_next(
        project_id=project.id,
        worker_id="worker-1",
        now=index_now,
        lease_until=index_now + timedelta(minutes=5),
    )

    assert result is not None
    assert not isinstance(result, IndexingBlockedResult)
    assert result.chunk_count >= 1
    assert (
        result.contextualized_chunk_count + result.reused_contextualized_chunk_count
        == result.chunk_count
    )
    assert result.embedded_chunk_count + result.reused_chunk_count == result.chunk_count
    assert (
        result.sparse_embedded_chunk_count + result.sparse_reused_chunk_count
        == result.chunk_count
    )

    chunks = session.scalars(select(Chunk)).all()
    assert len(chunks) == result.chunk_count
    assert all(chunk.contextual_summary for chunk in chunks)
    assert all(chunk.embedding is not None for chunk in chunks)
    sparse_rows = session.scalars(select(ChunkSparseEmbedding)).all()
    assert len(sparse_rows) == result.chunk_count

    index_job = JobRepository(session).list(
        project_id=project.id,
        job_type=INDEX_DOCUMENT_VERSION_JOB_TYPE,
    )[0]
    assert index_job.status == "succeeded"


def test_index_job_blocks_when_document_version_is_foreign() -> None:
    session = _make_session()
    project_a = ProjectRepository(session).create(name="a")
    project_b = ProjectRepository(session).create(name="b")
    source = SourceRepository(session).create(
        project_id=project_a.id,
        source_type="txt",
        external_id="a.txt",
        extra_metadata={"content": "private"},
    )
    document = DocumentRepository(session).create_document(
        project_id=project_a.id,
        source_id=source.id,
        stable_id=source.external_id,
    )
    version = DocumentRepository(session).create_version(
        project_id=project_a.id,
        document_id=document.id,
        version_number=1,
        normalized_text="private",
        content_hash="sha256:private",
        index_fingerprint="sha256:fp",
        parser_metadata={},
        extraction_metadata={},
    )
    job = JobRepository(session).create(
        project_id=project_b.id,
        job_type=INDEX_DOCUMENT_VERSION_JOB_TYPE,
        payload_json={
            "document_version_id": str(version.id),
            "source_id": str(source.id),
        },
        run_after=_run_time(),
    )
    session.commit()

    result = IndexingPipeline(
        session,
        dense_embedding_provider=FakeDenseEmbeddingProvider(),
        sparse_embedding_provider=FakeSparseEmbeddingProvider(),
    ).run_next(
        project_id=project_b.id,
        worker_id="worker-1",
        now=_run_time(),
        lease_until=_run_time() + timedelta(minutes=5),
    )

    assert isinstance(result, IndexingBlockedResult)
    assert result.job.id == job.id
    assert "does not belong to project" in result.error_message
    assert session.scalar(select(func.count()).select_from(Chunk)) == 0
