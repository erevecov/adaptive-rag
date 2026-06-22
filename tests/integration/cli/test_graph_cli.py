from __future__ import annotations

import json
from uuid import UUID

from typer.testing import CliRunner

from adaptive_rag.cli.app import app
from adaptive_rag.graph import GraphStoreHealth
from adaptive_rag.graph.operations import (
    GraphBackfillOperationReport,
    GraphRetrievalSmokeReport,
)


class ReadyGraphStore:
    backend = "neo4j"

    def __init__(self) -> None:
        self.close_calls = 0

    def health_check(self) -> GraphStoreHealth:
        return GraphStoreHealth(
            backend="neo4j",
            available=True,
            status="ready",
        )

    def expand_project_chunks(self, **_kwargs):
        return ()

    def close(self) -> None:
        self.close_calls += 1


class UnavailableGraphStore:
    backend = "neo4j"

    def health_check(self) -> GraphStoreHealth:
        return GraphStoreHealth(
            backend="neo4j",
            available=False,
            status="unavailable",
            error_code="graph_store_unavailable",
        )


def test_graph_neo4j_smoke_outputs_ready_json_without_secrets(monkeypatch) -> None:
    store = ReadyGraphStore()
    monkeypatch.setattr("adaptive_rag.cli.graph.get_cli_graph_store", lambda: store)
    monkeypatch.setattr(
        "adaptive_rag.cli.graph.get_settings",
        lambda: _settings(uri="neo4j+s://secret-host.databases.neo4j.io"),
    )

    result = CliRunner().invoke(app, ["graph", "neo4j-smoke"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data == {
        "backend": "neo4j",
        "available": True,
        "status": "ready",
        "error_code": None,
        "uri_scheme": "neo4j+s",
        "uri_kind": "managed_encrypted",
    }
    assert "secret-host" not in result.stdout
    assert "secret-password" not in result.stdout
    assert store.close_calls == 1


def test_graph_neo4j_smoke_exits_nonzero_when_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        "adaptive_rag.cli.graph.get_cli_graph_store",
        lambda: UnavailableGraphStore(),
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.graph.get_settings",
        lambda: _settings(uri="neo4j://localhost:7687"),
    )

    result = CliRunner().invoke(app, ["graph", "neo4j-smoke"])

    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data == {
        "backend": "neo4j",
        "available": False,
        "status": "unavailable",
        "error_code": "graph_store_unavailable",
        "uri_scheme": "neo4j",
        "uri_kind": "local_or_self_managed",
    }


def test_graph_backfill_outputs_operation_report(monkeypatch) -> None:
    project_id = "00000000-0000-0000-0000-000000000123"
    calls: list[dict[str, object]] = []

    def fake_run_graph_backfill_operation(**kwargs):
        calls.append(kwargs)
        return GraphBackfillOperationReport(
            project_id=UUID(project_id),
            backend="neo4j",
            operation="backfill",
            previous_status="disabled",
            status="ready",
            source_watermark="chunks:v1",
            duration_ms=125,
            node_count=9,
            relationship_count=8,
            error_code=None,
        )

    monkeypatch.setattr(
        "adaptive_rag.cli.graph.run_graph_backfill_operation",
        fake_run_graph_backfill_operation,
    )
    monkeypatch.setattr("adaptive_rag.cli.graph.get_cli_graph_store", lambda: object())
    monkeypatch.setattr(
        "adaptive_rag.cli.graph.session_scope",
        lambda: _session_scope(object()),
    )

    result = CliRunner().invoke(
        app,
        [
            "graph",
            "backfill",
            project_id,
            "--source-watermark",
            "chunks:v1",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data == {
        "project_id": project_id,
        "backend": "neo4j",
        "operation": "backfill",
        "previous_status": "disabled",
        "status": "ready",
        "source_watermark": "chunks:v1",
        "duration_ms": 125,
        "node_count": 9,
        "relationship_count": 8,
        "error_code": None,
    }
    assert calls[0]["operation"] == "backfill"


def test_graph_reindex_exits_nonzero_on_failed_report(monkeypatch) -> None:
    project_id = "00000000-0000-0000-0000-000000000123"

    def fake_run_graph_backfill_operation(**_kwargs):
        return GraphBackfillOperationReport(
            project_id=UUID(project_id),
            backend="neo4j",
            operation="reindex",
            previous_status="stale",
            status="failed",
            source_watermark="chunks:v2",
            duration_ms=500,
            node_count=None,
            relationship_count=None,
            error_code="graph_store_unavailable",
        )

    monkeypatch.setattr(
        "adaptive_rag.cli.graph.run_graph_backfill_operation",
        fake_run_graph_backfill_operation,
    )
    monkeypatch.setattr("adaptive_rag.cli.graph.get_cli_graph_store", lambda: object())
    monkeypatch.setattr(
        "adaptive_rag.cli.graph.session_scope",
        lambda: _session_scope(object()),
    )

    result = CliRunner().invoke(
        app,
        [
            "graph",
            "reindex",
            project_id,
            "--source-watermark",
            "chunks:v2",
        ],
    )

    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["operation"] == "reindex"
    assert data["status"] == "failed"
    assert data["error_code"] == "graph_store_unavailable"


def test_graph_retrieval_smoke_outputs_ready_report(monkeypatch) -> None:
    project_id = "00000000-0000-0000-0000-000000000123"
    chunk_id = "00000000-0000-0000-0000-000000000456"
    store = ReadyGraphStore()
    calls: list[dict[str, object]] = []

    def fake_run_graph_retrieval_smoke(**kwargs):
        calls.append(kwargs)
        return GraphRetrievalSmokeReport(
            project_id=UUID(project_id),
            backend="neo4j",
            status="ready",
            requested_strategy="graph",
            result_count=1,
            graph_result_count=1,
            citation_count=1,
            fallback_reason=None,
            latency_ms=42,
            limit=3,
            chunk_ids=(UUID(chunk_id),),
            source_external_ids=("alpha.md",),
        )

    monkeypatch.setattr(
        "adaptive_rag.cli.graph.run_graph_retrieval_smoke",
        fake_run_graph_retrieval_smoke,
    )
    monkeypatch.setattr("adaptive_rag.cli.graph.get_cli_graph_store", lambda: store)
    monkeypatch.setattr(
        "adaptive_rag.cli.graph.get_cli_dense_embedding_provider",
        lambda: object(),
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.graph.session_scope",
        lambda: _session_scope(object()),
    )

    result = CliRunner().invoke(
        app,
        [
            "graph",
            "retrieval-smoke",
            project_id,
            "--query",
            "alpha question",
            "--limit",
            "3",
            "--source-type",
            "markdown",
            "--tag",
            "docs",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data == {
        "project_id": project_id,
        "backend": "neo4j",
        "status": "ready",
        "requested_strategy": "graph",
        "result_count": 1,
        "graph_result_count": 1,
        "citation_count": 1,
        "fallback_reason": None,
        "latency_ms": 42,
        "limit": 3,
        "chunk_ids": [chunk_id],
        "source_external_ids": ["alpha.md"],
    }
    assert calls[0]["project_id"] == UUID(project_id)
    assert calls[0]["query"] == "alpha question"
    assert calls[0]["limit"] == 3
    assert calls[0]["metadata_filter"].source_type == "markdown"
    assert calls[0]["metadata_filter"].tags == ("docs",)
    assert calls[0]["graph_retriever"] is store
    assert store.close_calls == 1


def test_graph_retrieval_smoke_exits_nonzero_on_fallback_report(monkeypatch) -> None:
    project_id = "00000000-0000-0000-0000-000000000123"

    def fake_run_graph_retrieval_smoke(**_kwargs):
        return GraphRetrievalSmokeReport(
            project_id=UUID(project_id),
            backend="neo4j",
            status="fallback",
            requested_strategy="graph",
            result_count=2,
            graph_result_count=0,
            citation_count=2,
            fallback_reason="graph_projection_pending_backfill",
            latency_ms=50,
            limit=2,
            chunk_ids=(),
            source_external_ids=(),
        )

    monkeypatch.setattr(
        "adaptive_rag.cli.graph.run_graph_retrieval_smoke",
        fake_run_graph_retrieval_smoke,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.graph.get_cli_graph_store",
        lambda: ReadyGraphStore(),
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.graph.get_cli_dense_embedding_provider",
        lambda: object(),
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.graph.session_scope",
        lambda: _session_scope(object()),
    )

    result = CliRunner().invoke(
        app,
        ["graph", "retrieval-smoke", project_id, "--query", "alpha question"],
    )

    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["status"] == "fallback"
    assert data["fallback_reason"] == "graph_projection_pending_backfill"
    assert data["graph_result_count"] == 0


def _settings(*, uri: str):
    class SmokeSettings:
        neo4j_uri = uri

    return SmokeSettings()


class _session_scope:
    def __init__(self, session: object) -> None:
        self.session = session

    def __enter__(self) -> object:
        return self.session

    def __exit__(self, *_exc_info: object) -> bool:
        return False
