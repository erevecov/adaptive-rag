"""First-run smoke orchestration for local product onboarding."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag import authoring, ingestion_ops
from adaptive_rag.chat import ChatRequest, ChatRunner, ChatService
from adaptive_rag.chunking import ChunkingPipeline, ChunkingPipelineError
from adaptive_rag.contextualization import (
    ContextualizationPipeline,
    ContextualizationPipelineError,
)
from adaptive_rag.db.models import Job, Project, Source
from adaptive_rag.embeddings import (
    DenseEmbeddingPipeline,
    DenseEmbeddingPipelineError,
    DenseEmbeddingProvider,
    FakeSparseEmbeddingProvider,
    SparseEmbeddingPipeline,
    SparseEmbeddingPipelineError,
    SparseEmbeddingProvider,
)
from adaptive_rag.retrieval import RetrievalService

DEFAULT_PROJECT_NAME = "Adaptive RAG First Run"
DEFAULT_SOURCE_EXTERNAL_ID = "first-run.md"
DEFAULT_QUESTION = "What does the Adaptive RAG first run prove?"
DEFAULT_WORKER_ID = "first-run"
DEFAULT_CONTENT = """# Adaptive RAG first run

Adaptive RAG first run creates a local project, ingests Markdown, indexes
chunks, and answers cited questions without hosted providers.

## Evidence

The onboarding path proves authoring, ingestion, chunking, embeddings, and chat
are wired together for a local-first product flow.
"""


class FirstRunError(Exception):
    """Stable first-run error surfaced by CLI and future runbooks."""


@dataclass(frozen=True, slots=True)
class FirstRunReport:
    status: str
    project: Project
    source: Source
    job: Job
    question: str
    document_version_id: UUID
    chunk_count: int
    contextualized_chunk_count: int
    reused_contextualized_chunk_count: int
    embedded_chunk_count: int
    reused_chunk_count: int
    answer: str
    citation_count: int


def run_first_run_smoke(
    session: Session,
    *,
    dense_embedding_provider: DenseEmbeddingProvider,
    sparse_embedding_provider: SparseEmbeddingProvider | None = None,
    chat_runner: ChatRunner,
    project_name: str = DEFAULT_PROJECT_NAME,
    source_external_id: str = DEFAULT_SOURCE_EXTERNAL_ID,
    content: str = DEFAULT_CONTENT,
    question: str = DEFAULT_QUESTION,
    worker_id: str = DEFAULT_WORKER_ID,
) -> FirstRunReport:
    active_sparse_embedding_provider = (
        sparse_embedding_provider or FakeSparseEmbeddingProvider()
    )
    project = authoring.create_project(session, name=project_name)
    source = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id=source_external_id,
        tags=["first-run"],
        extra_metadata={"content": content},
    )
    job = ingestion_ops.enqueue_source_ingestion(
        session,
        project_id=project.id,
        source_id=source.id,
    )
    run = ingestion_ops.run_next_ingestion_job(
        session,
        project_id=project.id,
        worker_id=worker_id,
    )
    if run.status != "processed" or run.document_version_id is None:
        detail = run.error_message or run.status
        raise FirstRunError(f"first-run ingestion did not process: {detail}")

    try:
        chunk_result = ChunkingPipeline(session).chunk_document_version(
            project_id=project.id,
            document_version_id=run.document_version_id,
        )
        contextualization_result = (
            ContextualizationPipeline(session).contextualize_document_version(
                project_id=project.id,
                document_version_id=run.document_version_id,
            )
        )
        embedding_result = DenseEmbeddingPipeline(
            session,
            provider=dense_embedding_provider,
        ).embed_document_version(
            project_id=project.id,
            document_version_id=run.document_version_id,
        )
        SparseEmbeddingPipeline(
            session,
            provider=active_sparse_embedding_provider,
        ).embed_document_version(
            project_id=project.id,
            document_version_id=run.document_version_id,
        )
    except (
        ChunkingPipelineError,
        ContextualizationPipelineError,
        DenseEmbeddingPipelineError,
        SparseEmbeddingPipelineError,
    ) as exc:
        raise FirstRunError(str(exc)) from exc

    chat = ChatService(
        runner=chat_runner,
        retrieval_service=RetrievalService(
            session,
            provider=dense_embedding_provider,
            sparse_provider=active_sparse_embedding_provider,
        ),
    ).respond(
        ChatRequest(
            project_id=project.id,
            message=question,
            retrieval_limit=5,
        )
    )
    if not chat.citations:
        raise FirstRunError("first-run chat returned no citations")

    return FirstRunReport(
        status="succeeded",
        project=project,
        source=source,
        job=job,
        question=question,
        document_version_id=run.document_version_id,
        chunk_count=len(chunk_result.chunks),
        contextualized_chunk_count=(
            contextualization_result.contextualized_chunk_count
        ),
        reused_contextualized_chunk_count=(
            contextualization_result.reused_contextualized_chunk_count
        ),
        embedded_chunk_count=embedding_result.embedded_chunk_count,
        reused_chunk_count=embedding_result.reused_chunk_count,
        answer=chat.answer,
        citation_count=len(chat.citations),
    )


def first_run_report_payload(report: FirstRunReport) -> dict[str, object]:
    return {
        "status": report.status,
        "project": authoring.project_payload(report.project),
        "source": authoring.source_payload(report.source),
        "job": ingestion_ops.job_payload(report.job),
        "question": report.question,
        "document_version_id": str(report.document_version_id),
        "chunk_count": report.chunk_count,
        "contextualized_chunk_count": report.contextualized_chunk_count,
        "reused_contextualized_chunk_count": (
            report.reused_contextualized_chunk_count
        ),
        "embedded_chunk_count": report.embedded_chunk_count,
        "reused_chunk_count": report.reused_chunk_count,
        "answer": report.answer,
        "citation_count": report.citation_count,
        "next_commands": [
            (
                "adaptive-rag chat ask "
                f"--project-id {report.project.id} --message "
                f"{_shell_quote(report.question)}"
            ),
            f"adaptive-rag sources list --project-id {report.project.id}",
            f"adaptive-rag jobs list --project-id {report.project.id}",
        ],
    }


def _shell_quote(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'
