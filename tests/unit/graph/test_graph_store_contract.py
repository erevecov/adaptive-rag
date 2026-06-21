from __future__ import annotations

from uuid import uuid4

import pytest

from adaptive_rag.graph import (
    DisabledGraphStore,
    FakeGraphStore,
    GraphStoreConfigurationError,
    GraphStoreQueryError,
    GraphStoreUnavailableError,
    should_use_dense_fallback,
)


def test_disabled_graph_store_reports_disabled_health_without_network() -> None:
    store = DisabledGraphStore()

    health = store.health_check()

    assert health.backend == "disabled"
    assert health.available is False
    assert health.status == "disabled"
    assert health.error_code is None


def test_fake_graph_store_records_backfill_and_delete_by_project() -> None:
    project_id = uuid4()
    store = FakeGraphStore(backend="neo4j")

    backfill = store.backfill_project_graph(
        project_id=project_id,
        source_watermark="chunks:v1",
    )
    store.delete_project_graph(project_id=project_id)

    assert backfill.project_id == project_id
    assert backfill.backend == "neo4j"
    assert backfill.status == "ready"
    assert backfill.source_watermark == "chunks:v1"
    assert store.backfill_requests == ((project_id, "chunks:v1"),)
    assert store.delete_requests == (project_id,)


def test_graph_store_errors_have_stable_codes() -> None:
    errors = [
        GraphStoreConfigurationError("missing URI"),
        GraphStoreUnavailableError("service unavailable"),
        GraphStoreQueryError("query failed"),
    ]

    assert [error.error_code for error in errors] == [
        "graph_store_misconfigured",
        "graph_store_unavailable",
        "graph_store_query_failed",
    ]


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("disabled", True),
        ("pending_backfill", True),
        ("indexing", True),
        ("ready", False),
        ("stale", True),
        ("failed", True),
    ],
)
def test_dense_fallback_is_required_until_projection_is_ready(
    status: str,
    expected: bool,
) -> None:
    assert should_use_dense_fallback(status) is expected
