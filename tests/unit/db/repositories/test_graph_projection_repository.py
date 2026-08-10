"""Tests para readiness/backfill de graph projection."""

from __future__ import annotations

from datetime import UTC, datetime

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Graphprojection, Workspace
from adaptive_rag.db.repositories import GraphprojectionRepository, WorkspaceRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Workspace.__table__, Graphprojection.__table__],
    )
    return create_session_factory(engine)()


def test_ensure_creates_disabled_projection_without_committing() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    repo = GraphprojectionRepository(session)

    projection = repo.ensure(workspace_id=workspace.id)

    assert projection.id is not None
    assert projection.workspace_id == workspace.id
    assert projection.backend == "neo4j"
    assert projection.status == "disabled"

    session.rollback()
    session.expunge_all()

    assert repo.get(workspace_id=workspace.id) is None


def test_mark_pending_backfill_sets_watermark_and_versions() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    repo = GraphprojectionRepository(session)

    projection = repo.mark_pending_backfill(
        workspace_id=workspace.id,
        source_watermark="chunks:42",
        schema_version="graph-store-v2",
        extractor_version="entity-extractor-v3",
    )

    assert projection.status == "pending_backfill"
    assert projection.source_watermark == "chunks:42"
    assert projection.schema_version == "graph-store-v2"
    assert projection.extractor_version == "entity-extractor-v3"
    assert projection.error_code is None
    assert projection.error_message is None


def test_mark_ready_records_indexed_at_and_clears_previous_error() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    indexed_at = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
    repo = GraphprojectionRepository(session)
    repo.mark_failed(
        workspace_id=workspace.id,
        error_code="graph_store_unavailable",
        error_message="temporary outage",
    )

    projection = repo.mark_ready(
        workspace_id=workspace.id,
        source_watermark="chunks:43",
        indexed_at=indexed_at,
    )

    assert projection.status == "ready"
    assert projection.source_watermark == "chunks:43"
    assert projection.last_indexed_at == indexed_at
    assert projection.error_code is None
    assert projection.error_message is None


def test_graph_projection_repository_is_workspace_scoped() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    other_workspace = WorkspaceRepository(session).create(name="other")
    repo = GraphprojectionRepository(session)
    projection = repo.mark_pending_backfill(
        workspace_id=workspace.id,
        source_watermark="chunks:42",
    )
    session.commit()

    assert repo.get(workspace_id=workspace.id).id == projection.id
    assert repo.get(workspace_id=other_workspace.id) is None
