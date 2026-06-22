"""Operational graph backfill/reindex orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.db.repositories import GraphProjectionRepository
from adaptive_rag.graph.store import GraphProjectionStatus, GraphStore, GraphStoreError

GraphBackfillOperationName = Literal["backfill", "reindex"]


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


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _duration_ms(start: float, end: float) -> int:
    return max(0, round((end - start) * 1000))
