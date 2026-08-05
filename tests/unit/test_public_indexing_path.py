"""Public product path: authoring → jobs → chunks → cited chat."""

from __future__ import annotations

import inspect

from sqlalchemy import select

from adaptive_rag import authoring, first_run, ingestion_ops
from adaptive_rag.chat import RetrievalGroundedChatRunner
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
from adaptive_rag.db.repositories import JobRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.embeddings import (
    FakeDenseEmbeddingProvider,
    FakeSparseEmbeddingProvider,
)
from adaptive_rag.ingestion.indexing import INDEX_DOCUMENT_VERSION_JOB_TYPE
from adaptive_rag.ingestion.pipeline import INGEST_SOURCE_JOB_TYPE


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


def test_public_path_source_worker_chunks_chat_citations() -> None:
    session = _make_session()
    dense = FakeDenseEmbeddingProvider()
    sparse = FakeSparseEmbeddingProvider()

    project = authoring.create_project(session, name="Public Index Demo")
    source = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id="public.md",
        extra_metadata={
            "content": (
                "# Public path\n\n"
                "The public indexing job makes Adaptive RAG citations possible."
            )
        },
    )
    ingest_job = ingestion_ops.enqueue_source_ingestion(
        session,
        project_id=project.id,
        source_id=source.id,
    )

    reports = ingestion_ops.run_ingestion_family_until_idle(
        session,
        project_id=project.id,
        worker_id="public-worker",
        dense_embedding_provider=dense,
        sparse_embedding_provider=sparse,
    )

    assert len(reports) == 2
    assert reports[0].job_type == INGEST_SOURCE_JOB_TYPE
    assert reports[0].status == "processed"
    assert reports[1].job_type == INDEX_DOCUMENT_VERSION_JOB_TYPE
    assert reports[1].status == "processed"
    assert reports[1].chunk_count is not None and reports[1].chunk_count >= 1

    chunks = session.scalars(select(Chunk)).all()
    assert len(chunks) == reports[1].chunk_count
    assert all(chunk.embedding is not None for chunk in chunks)
    assert all(chunk.contextual_summary for chunk in chunks)

    jobs = JobRepository(session).list(project_id=project.id)
    by_type = {job.job_type: job for job in jobs}
    assert by_type[INGEST_SOURCE_JOB_TYPE].id == ingest_job.id
    assert by_type[INGEST_SOURCE_JOB_TYPE].status == "succeeded"
    assert by_type[INDEX_DOCUMENT_VERSION_JOB_TYPE].status == "succeeded"

    report = first_run.run_first_run_smoke(
        session,
        dense_embedding_provider=FakeDenseEmbeddingProvider(),
        sparse_embedding_provider=FakeSparseEmbeddingProvider(),
        chat_runner=RetrievalGroundedChatRunner(),
        project_name="First Run Via Jobs",
        source_external_id="first-run-jobs.md",
        content=(
            "# First run via jobs\n\n"
            "Public jobs prove authoring, indexing, and cited chat share one path."
        ),
        question="What do public jobs prove?",
        worker_id="first-run-jobs",
    )
    assert report.status == "succeeded"
    assert report.chunk_count >= 1
    assert report.citation_count >= 1
    assert "public jobs" in report.answer.lower() or "path" in report.answer.lower()


def test_first_run_and_acceptance_do_not_call_inline_chunking_pipelines() -> None:
    first_run_source = inspect.getsource(first_run)
    assert "ChunkingPipeline" not in first_run_source
    assert "DenseEmbeddingPipeline" not in first_run_source
    assert "SparseEmbeddingPipeline" not in first_run_source
    assert "ContextualizationPipeline" not in first_run_source
    assert "run_ingestion_family_until_idle" in first_run_source

    from adaptive_rag import acceptance

    acceptance_source = inspect.getsource(acceptance)
    assert "ChunkingPipeline" not in acceptance_source
    assert "DenseEmbeddingPipeline" not in acceptance_source
    assert "run_ingestion_family_until_idle" in acceptance_source
