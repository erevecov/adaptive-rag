"""First-party typed handlers registered with the general job worker."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.contextualization import Contextualizer
from adaptive_rag.embeddings import DenseEmbeddingProvider, SparseEmbeddingProvider
from adaptive_rag.ingestion.indexing import (
    IndexingPipeline,
    IndexingPipelineError,
)
from adaptive_rag.ingestion.pipeline import (
    IngestionPipeline,
)
from adaptive_rag.ingestion.types import IngestionPipelineError
from adaptive_rag.ingestion.url_fetch_policy import URLFetchPolicyError
from adaptive_rag.jobs.errors import BlockedJobError
from adaptive_rag.jobs.registry import JobHandlerDefinition, JobRegistry
from adaptive_rag.jobs.service import EnqueueJobRequest, JobService
from adaptive_rag.jobs.types import JobContext, RetryPolicy
from adaptive_rag.provider_pricing import sync_provider_model_pricing


class IngestSourcePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: UUID


class IndexDocumentVersionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_version_id: UUID
    source_id: UUID | None = None


class ProviderPricingSyncPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


def build_ingestion_registry(
    *,
    session_factory: sessionmaker[Session],
    dense_embedding_provider: DenseEmbeddingProvider | None = None,
    sparse_embedding_provider: SparseEmbeddingProvider | None = None,
    contextualizer: Contextualizer | None = None,
    lease_seconds: int | None = None,
) -> JobRegistry:
    registry = JobRegistry()

    def ingest_source(
        context: JobContext,
        raw_payload: BaseModel,
    ) -> dict[str, object]:
        payload = IngestSourcePayload.model_validate(raw_payload)
        if context.workspace_id is None:
            raise BlockedJobError("ingest_source requires workspace scope")
        try:
            with session_factory() as session:
                result = IngestionPipeline(session).process_source(
                    workspace_id=context.workspace_id,
                    source_id=payload.source_id,
                )
                JobService(session=session, registry=registry).enqueue(
                    EnqueueJobRequest.workspace(
                        workspace_id=context.workspace_id,
                        job_type="index_document_version",
                        payload={
                            "document_version_id": str(result.document_version.id),
                            "source_id": str(result.source.id),
                        },
                        idempotency_key=(
                            f"document-version:{result.document_version.id}"
                        ),
                    )
                )
                session.commit()
                return {
                    "source_id": str(result.source.id),
                    "document_id": str(result.document.id),
                    "document_version_id": str(result.document_version.id),
                    "created_document_version": result.created_document_version,
                }
        except (IngestionPipelineError, URLFetchPolicyError, IntegrityError) as exc:
            raise BlockedJobError(str(exc)) from exc

    def index_document_version(
        context: JobContext,
        raw_payload: BaseModel,
    ) -> dict[str, object]:
        payload = IndexDocumentVersionPayload.model_validate(raw_payload)
        if context.workspace_id is None:
            raise BlockedJobError("index_document_version requires workspace scope")
        try:
            with session_factory() as session:
                result = IndexingPipeline(
                    session,
                    dense_embedding_provider=dense_embedding_provider,
                    sparse_embedding_provider=sparse_embedding_provider,
                    contextualizer=contextualizer,
                ).index_document_version(
                    workspace_id=context.workspace_id,
                    document_version_id=payload.document_version_id,
                    source_id=payload.source_id,
                )
                session.commit()
                return {
                    "document_version_id": str(result.document_version.id),
                    "source_id": (
                        None if result.source_id is None else str(result.source_id)
                    ),
                    "chunk_count": result.chunk_count,
                    "contextualized_chunk_count": (result.contextualized_chunk_count),
                    "reused_contextualized_chunk_count": (
                        result.reused_contextualized_chunk_count
                    ),
                    "embedded_chunk_count": result.embedded_chunk_count,
                    "reused_chunk_count": result.reused_chunk_count,
                    "sparse_embedded_chunk_count": (result.sparse_embedded_chunk_count),
                    "sparse_reused_chunk_count": result.sparse_reused_chunk_count,
                }
        except IndexingPipelineError as exc:
            raise BlockedJobError(str(exc)) from exc

    def provider_model_pricing_sync(
        context: JobContext,
        _raw_payload: BaseModel,
    ) -> dict[str, object]:
        if context.workspace_id is not None:
            raise BlockedJobError("provider_model_pricing_sync requires system scope")
        with session_factory() as session:
            report = sync_provider_model_pricing(session, dry_run=False)
            session.commit()
            return report.as_dict()

    registry.register(
        JobHandlerDefinition(
            name="ingest_source",
            version=1,
            payload_model=IngestSourcePayload,
            handler=ingest_source,
            queue_name="ingestion",
            retry_policy=RetryPolicy(max_retries=2),
            lease_seconds=lease_seconds,
            allowed_scopes=frozenset({"workspace"}),
            allow_manual_enqueue=True,
            minimum_manual_role="contributor",
        )
    )
    registry.register(
        JobHandlerDefinition(
            name="index_document_version",
            version=1,
            payload_model=IndexDocumentVersionPayload,
            handler=index_document_version,
            queue_name="ingestion",
            retry_policy=RetryPolicy(max_retries=2),
            lease_seconds=lease_seconds,
            allowed_scopes=frozenset({"workspace"}),
        )
    )
    registry.register(
        JobHandlerDefinition(
            name="provider_model_pricing_sync",
            version=1,
            payload_model=ProviderPricingSyncPayload,
            handler=provider_model_pricing_sync,
            queue_name="system",
            retry_policy=RetryPolicy(max_retries=3),
            lease_seconds=lease_seconds,
            allowed_scopes=frozenset({"system"}),
            allow_manual_enqueue=True,
        )
    )
    return registry


__all__ = [
    "IndexDocumentVersionPayload",
    "IngestSourcePayload",
    "ProviderPricingSyncPayload",
    "build_ingestion_registry",
]
