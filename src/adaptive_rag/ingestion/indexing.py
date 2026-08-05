"""Public indexing jobs: chunk → contextualize → dense/sparse embeddings."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.chunking import ChunkingPipeline, ChunkingPipelineError
from adaptive_rag.contextualization import (
    ContextualizationPipeline,
    ContextualizationPipelineError,
    Contextualizer,
    DeterministicContextualizer,
)
from adaptive_rag.db.models import DocumentVersion, Job
from adaptive_rag.db.repositories import JobRepository
from adaptive_rag.embeddings import (
    DenseEmbeddingPipeline,
    DenseEmbeddingPipelineError,
    DenseEmbeddingProvider,
    SparseEmbeddingPipeline,
    SparseEmbeddingPipelineError,
    SparseEmbeddingProvider,
)

INDEX_DOCUMENT_VERSION_JOB_TYPE = "index_document_version"


class IndexingPipelineError(ValueError):
    """Error no retryable de indexing publico."""


@dataclass(frozen=True, slots=True)
class IndexingRunResult:
    job: Job
    document_version: DocumentVersion
    source_id: UUID | None
    chunk_count: int
    contextualized_chunk_count: int
    reused_contextualized_chunk_count: int
    embedded_chunk_count: int
    reused_chunk_count: int
    sparse_embedded_chunk_count: int
    sparse_reused_chunk_count: int


@dataclass(frozen=True, slots=True)
class IndexingBlockedResult:
    job: Job
    error_message: str


class IndexingPipeline:
    """Worker-facing pipeline for jobs `index_document_version`."""

    def __init__(
        self,
        session: Session,
        *,
        dense_embedding_provider: DenseEmbeddingProvider | None = None,
        sparse_embedding_provider: SparseEmbeddingProvider | None = None,
        contextualizer: Contextualizer | None = None,
    ) -> None:
        self._session = session
        self._job_repo = JobRepository(session)
        self._dense_embedding_provider = dense_embedding_provider
        self._sparse_embedding_provider = sparse_embedding_provider
        self._contextualizer = contextualizer

    def run_next(
        self,
        *,
        project_id: UUID,
        worker_id: str,
        now: datetime,
        lease_until: datetime,
    ) -> IndexingRunResult | IndexingBlockedResult | None:
        job = self._job_repo.lease_next(
            project_id=project_id,
            worker_id=worker_id,
            now=now,
            lease_until=lease_until,
            job_type=INDEX_DOCUMENT_VERSION_JOB_TYPE,
        )
        if job is None:
            return None
        return self._finalize_job(project_id=project_id, job=job)

    def process_leased_job(
        self,
        *,
        project_id: UUID,
        job: Job,
    ) -> IndexingRunResult | IndexingBlockedResult:
        if job.job_type != INDEX_DOCUMENT_VERSION_JOB_TYPE:
            raise IndexingPipelineError(
                f"unsupported job_type for indexing pipeline: {job.job_type}"
            )
        return self._finalize_job(project_id=project_id, job=job)

    def _finalize_job(
        self,
        *,
        project_id: UUID,
        job: Job,
    ) -> IndexingRunResult | IndexingBlockedResult:
        try:
            result = self._process_job(project_id=project_id, job=job)
        except (
            IndexingPipelineError,
            ChunkingPipelineError,
            ContextualizationPipelineError,
            DenseEmbeddingPipelineError,
            SparseEmbeddingPipelineError,
        ) as exc:
            blocked_job = self._job_repo.block(
                project_id=project_id,
                job_id=job.id,
                reason=str(exc),
            )
            return IndexingBlockedResult(job=blocked_job, error_message=str(exc))

        self._job_repo.complete(project_id=project_id, job_id=job.id)
        return result

    def _process_job(self, *, project_id: UUID, job: Job) -> IndexingRunResult:
        document_version_id = _document_version_id_from_payload(job.payload_json)
        source_id = _optional_source_id_from_payload(job.payload_json)

        dense_provider = self._resolve_dense_provider(project_id=project_id)
        sparse_provider = self._resolve_sparse_provider(project_id=project_id)
        contextualizer = self._resolve_contextualizer(project_id=project_id)

        chunk_result = ChunkingPipeline(self._session).chunk_document_version(
            project_id=project_id,
            document_version_id=document_version_id,
        )
        contextualization_result = ContextualizationPipeline(
            self._session,
            contextualizer=contextualizer,
        ).contextualize_document_version(
            project_id=project_id,
            document_version_id=document_version_id,
        )
        dense_result = DenseEmbeddingPipeline(
            self._session,
            provider=dense_provider,
        ).embed_document_version(
            project_id=project_id,
            document_version_id=document_version_id,
        )
        sparse_result = SparseEmbeddingPipeline(
            self._session,
            provider=sparse_provider,
        ).embed_document_version(
            project_id=project_id,
            document_version_id=document_version_id,
        )

        return IndexingRunResult(
            job=job,
            document_version=chunk_result.document_version,
            source_id=source_id,
            chunk_count=len(chunk_result.chunks),
            contextualized_chunk_count=(
                contextualization_result.contextualized_chunk_count
            ),
            reused_contextualized_chunk_count=(
                contextualization_result.reused_contextualized_chunk_count
            ),
            embedded_chunk_count=dense_result.embedded_chunk_count,
            reused_chunk_count=dense_result.reused_chunk_count,
            sparse_embedded_chunk_count=sparse_result.embedded_chunk_count,
            sparse_reused_chunk_count=sparse_result.reused_chunk_count,
        )

    def _resolve_dense_provider(
        self, *, project_id: UUID
    ) -> DenseEmbeddingProvider:
        if self._dense_embedding_provider is not None:
            return self._dense_embedding_provider
        from adaptive_rag.runtime.factories import get_dense_embedding_provider

        return get_dense_embedding_provider(
            project_id=project_id,
            session=self._session,
        )

    def _resolve_sparse_provider(
        self, *, project_id: UUID
    ) -> SparseEmbeddingProvider:
        if self._sparse_embedding_provider is not None:
            return self._sparse_embedding_provider
        from adaptive_rag.runtime.factories import get_sparse_embedding_provider

        return get_sparse_embedding_provider(
            project_id=project_id,
            session=self._session,
        )

    def _resolve_contextualizer(self, *, project_id: UUID) -> Contextualizer:
        if self._contextualizer is not None:
            return self._contextualizer
        # Injected embedding providers mean a controlled/test path: keep
        # contextualization deterministic without requiring runtime settings tables.
        if (
            self._dense_embedding_provider is not None
            or self._sparse_embedding_provider is not None
        ):
            return DeterministicContextualizer()
        from adaptive_rag.runtime.factories import get_contextualizer

        return get_contextualizer(project_id=project_id, session=self._session)


def enqueue_index_document_version_job(
    session: Session,
    *,
    project_id: UUID,
    document_version_id: UUID,
    source_id: UUID | None = None,
    priority: int = 0,
    max_attempts: int = 3,
) -> Job:
    payload: dict[str, Any] = {"document_version_id": str(document_version_id)}
    if source_id is not None:
        payload["source_id"] = str(source_id)
    return JobRepository(session).create(
        project_id=project_id,
        job_type=INDEX_DOCUMENT_VERSION_JOB_TYPE,
        payload_json=payload,
        priority=priority,
        max_attempts=max_attempts,
    )


def _document_version_id_from_payload(payload: Mapping[str, Any] | None) -> UUID:
    if payload is None:
        raise IndexingPipelineError("index_document_version job payload is required")

    raw_id = payload.get("document_version_id")
    if not isinstance(raw_id, str):
        raise IndexingPipelineError(
            "index_document_version job requires string document_version_id"
        )
    try:
        return UUID(raw_id)
    except ValueError as exc:
        raise IndexingPipelineError(
            "index_document_version job document_version_id is invalid"
        ) from exc


def _optional_source_id_from_payload(payload: Mapping[str, Any] | None) -> UUID | None:
    if payload is None:
        return None
    raw_source_id = payload.get("source_id")
    if not isinstance(raw_source_id, str):
        return None
    try:
        return UUID(raw_source_id)
    except ValueError:
        return None
