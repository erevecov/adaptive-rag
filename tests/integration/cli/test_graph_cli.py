from __future__ import annotations

import json

from typer.testing import CliRunner

from adaptive_rag.cli.app import app
from adaptive_rag.graph import GraphStoreHealth


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


def _settings(*, uri: str):
    class SmokeSettings:
        neo4j_uri = uri

    return SmokeSettings()
