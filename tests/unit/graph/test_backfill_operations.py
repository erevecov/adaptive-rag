from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import GraphProjection, Project
from adaptive_rag.db.repositories import GraphProjectionRepository, ProjectRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.graph import GraphBackfillResult, GraphStoreUnavailableError
from adaptive_rag.graph.operations import run_graph_backfill_operation


class RecordingBackfillGraphStore:
    backend = "neo4j"

    def __init__(
        self,
        *,
        node_count: int = 7,
        relationship_count: int = 6,
        failure: Exception | None = None,
    ) -> None:
        self.node_count = node_count
        self.relationship_count = relationship_count
        self.failure = failure
        self.requests: list[tuple[UUID, str]] = []

    def backfill_project_graph(
        self,
        *,
        project_id: UUID,
        source_watermark: str,
    ) -> GraphBackfillResult:
        self.requests.append((project_id, source_watermark))
        if self.failure is not None:
            raise self.failure
        return GraphBackfillResult(
            project_id=project_id,
            backend="neo4j",
            status="ready",
            source_watermark=source_watermark,
            node_count=self.node_count,
            relationship_count=self.relationship_count,
        )


def test_run_graph_backfill_operation_marks_projection_ready() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    store = RecordingBackfillGraphStore(node_count=9, relationship_count=8)
    indexed_at = datetime(2026, 6, 22, 16, 0, tzinfo=UTC)

    report = run_graph_backfill_operation(
        session=session,
        graph_store=store,
        project_id=project.id,
        source_watermark="chunks:v2",
        operation="backfill",
        now=lambda: indexed_at,
        monotonic=_monotonic(10.0, 10.125),
    )

    projection = GraphProjectionRepository(session).get(project_id=project.id)
    assert report.project_id == project.id
    assert report.backend == "neo4j"
    assert report.operation == "backfill"
    assert report.previous_status == "disabled"
    assert report.status == "ready"
    assert report.source_watermark == "chunks:v2"
    assert report.duration_ms == 125
    assert report.node_count == 9
    assert report.relationship_count == 8
    assert report.error_code is None
    assert store.requests == [(project.id, "chunks:v2")]
    assert projection is not None
    assert projection.status == "ready"
    assert projection.source_watermark == "chunks:v2"
    assert projection.last_indexed_at is not None
    assert projection.last_indexed_at.replace(tzinfo=UTC) == indexed_at
    assert projection.error_code is None


def test_run_graph_backfill_operation_marks_projection_failed_on_store_error() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    store = RecordingBackfillGraphStore(
        failure=GraphStoreUnavailableError("neo4j graph store unavailable")
    )

    report = run_graph_backfill_operation(
        session=session,
        graph_store=store,
        project_id=project.id,
        source_watermark="chunks:v3",
        operation="backfill",
        now=lambda: datetime(2026, 6, 22, 16, 1, tzinfo=UTC),
        monotonic=_monotonic(20.0, 20.5),
    )

    projection = GraphProjectionRepository(session).get(project_id=project.id)
    assert report.status == "failed"
    assert report.error_code == "graph_store_unavailable"
    assert report.duration_ms == 500
    assert report.node_count is None
    assert report.relationship_count is None
    assert projection is not None
    assert projection.status == "failed"
    assert projection.error_code == "graph_store_unavailable"
    assert projection.error_message == "neo4j graph store unavailable"


def test_run_graph_backfill_operation_reindexes_existing_stale_projection() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    repo = GraphProjectionRepository(session)
    repo.mark_stale(project_id=project.id, source_watermark="chunks:old")
    store = RecordingBackfillGraphStore(node_count=3, relationship_count=2)

    report = run_graph_backfill_operation(
        session=session,
        graph_store=store,
        project_id=project.id,
        source_watermark="chunks:new",
        operation="reindex",
        now=lambda: datetime(2026, 6, 22, 16, 2, tzinfo=UTC),
        monotonic=_monotonic(30.0, 30.25),
    )

    projection = repo.get(project_id=project.id)
    assert report.operation == "reindex"
    assert report.previous_status == "stale"
    assert report.status == "ready"
    assert report.duration_ms == 250
    assert projection is not None
    assert projection.status == "ready"
    assert projection.source_watermark == "chunks:new"


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Project.__table__, GraphProjection.__table__],
    )
    return create_session_factory(engine)()


def _monotonic(*values: float) -> Callable[[], float]:
    active_values = iter(values)
    return lambda: next(active_values)
