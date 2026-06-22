"""Operational graph backfill/reindex orchestration."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.db.repositories import GraphProjectionRepository
from adaptive_rag.graph.store import (
    GraphProjectionStatus,
    GraphRetriever,
    GraphStore,
    GraphStoreError,
)

if TYPE_CHECKING:
    from adaptive_rag.embeddings import DenseEmbeddingProvider
    from adaptive_rag.retrieval import RetrievalMetadataFilter, RetrievalSearchResult

GraphBackfillOperationName = Literal["backfill", "reindex"]
GraphRetrievalSmokeStatus = Literal["ready", "fallback", "no_results"]


@dataclass(frozen=True, slots=True)
class GraphBackfillOperationReport:
    """Serializable report for a project-scoped graph rebuild operation."""

    project_id: UUID
    backend: Literal["neo4j"]
    operation: GraphBackfillOperationName
    previous_status: str
    status: GraphProjectionStatus
    source_watermark: str
    duration_ms: int
    node_count: int | None
    relationship_count: int | None
    error_code: str | None


@dataclass(frozen=True, slots=True)
class GraphRetrievalSmokeReport:
    """Serializable report for a project-scoped graph retrieval smoke."""

    project_id: UUID
    backend: Literal["neo4j"]
    status: GraphRetrievalSmokeStatus
    requested_strategy: Literal["graph"]
    result_count: int
    graph_result_count: int
    citation_count: int
    fallback_reason: str | None
    latency_ms: int
    limit: int
    chunk_ids: tuple[UUID, ...]
    source_external_ids: tuple[str, ...]


def run_graph_backfill_operation(
    *,
    session: Session,
    graph_store: GraphStore,
    project_id: UUID,
    source_watermark: str,
    operation: GraphBackfillOperationName,
    now: Callable[[], datetime] | None = None,
    monotonic: Callable[[], float] | None = None,
) -> GraphBackfillOperationReport:
    """Run a graph rebuild and persist projection readiness transitions."""

    now_fn = now or _utc_now
    monotonic_fn = monotonic or perf_counter
    repo = GraphProjectionRepository(session)
    previous_projection = repo.get(project_id=project_id)
    previous_status = (
        previous_projection.status if previous_projection is not None else "disabled"
    )
    start = monotonic_fn()

    repo.mark_pending_backfill(
        project_id=project_id,
        source_watermark=source_watermark,
    )
    session.commit()
    repo.mark_indexing(project_id=project_id)
    session.commit()

    try:
        result = graph_store.backfill_project_graph(
            project_id=project_id,
            source_watermark=source_watermark,
        )
    except GraphStoreError as exc:
        duration_ms = _duration_ms(start, monotonic_fn())
        repo.mark_failed(
            project_id=project_id,
            error_code=exc.error_code,
            error_message=str(exc),
        )
        session.commit()
        return GraphBackfillOperationReport(
            project_id=project_id,
            backend="neo4j",
            operation=operation,
            previous_status=previous_status,
            status="failed",
            source_watermark=source_watermark,
            duration_ms=duration_ms,
            node_count=None,
            relationship_count=None,
            error_code=exc.error_code,
        )

    repo.mark_ready(
        project_id=project_id,
        source_watermark=result.source_watermark,
        indexed_at=now_fn(),
    )
    session.commit()
    return GraphBackfillOperationReport(
        project_id=project_id,
        backend="neo4j",
        operation=operation,
        previous_status=previous_status,
        status="ready",
        source_watermark=result.source_watermark,
        duration_ms=_duration_ms(start, monotonic_fn()),
        node_count=result.node_count,
        relationship_count=result.relationship_count,
        error_code=None,
    )


def run_graph_retrieval_smoke(
    *,
    session: Session,
    provider: DenseEmbeddingProvider,
    graph_retriever: GraphRetriever,
    project_id: UUID,
    query: str,
    limit: int,
    metadata_filter: RetrievalMetadataFilter | None = None,
    monotonic: Callable[[], float] | None = None,
) -> GraphRetrievalSmokeReport:
    """Run a graph retrieval smoke and summarize graph/fallback behavior."""

    from adaptive_rag.retrieval import RetrievalSearchRequest, RetrievalService

    monotonic_fn = monotonic or perf_counter
    start = monotonic_fn()
    service = RetrievalService(
        session,
        provider=provider,
        graph_retriever=graph_retriever,
    )
    results = service.search(
        RetrievalSearchRequest(
            project_id=project_id,
            query=query,
            limit=limit,
            metadata_filter=metadata_filter,
            strategy="graph",
        )
    )
    fallback_reason = _fallback_reason(results)
    graph_result_count = sum(
        1
        for result in results
        if result.strategy == "graph" and result.fallback_reason is None
    )
    return GraphRetrievalSmokeReport(
        project_id=project_id,
        backend="neo4j",
        status=_retrieval_smoke_status(
            graph_result_count=graph_result_count,
            fallback_reason=fallback_reason,
        ),
        requested_strategy="graph",
        result_count=len(results),
        graph_result_count=graph_result_count,
        citation_count=len(results),
        fallback_reason=fallback_reason,
        latency_ms=_duration_ms(start, monotonic_fn()),
        limit=limit,
        chunk_ids=tuple(result.chunk_id for result in results),
        source_external_ids=tuple(
            result.citation.source_external_id for result in results
        ),
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _duration_ms(start: float, end: float) -> int:
    return max(0, round((end - start) * 1000))


def _fallback_reason(results: Sequence[RetrievalSearchResult]) -> str | None:
    reasons = sorted(
        {
            result.fallback_reason
            for result in results
            if result.fallback_reason is not None
        }
    )
    return reasons[0] if reasons else None


def _retrieval_smoke_status(
    *,
    graph_result_count: int,
    fallback_reason: str | None,
) -> GraphRetrievalSmokeStatus:
    if fallback_reason is not None:
        return "fallback"
    if graph_result_count > 0:
        return "ready"
    return "no_results"
