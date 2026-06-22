from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from neo4j.exceptions import AuthError, ServiceUnavailable

from adaptive_rag.config.settings import Settings
from adaptive_rag.graph import (
    DisabledGraphStore,
    GraphStoreConfigurationError,
    GraphStoreUnavailableError,
    Neo4jGraphStore,
    get_graph_store,
)


class FakeNeo4jDriver:
    def __init__(self, *, failure: Exception | None = None) -> None:
        self.failure = failure
        self.verify_calls = 0
        self.execute_queries: list[tuple[str, dict[str, Any]]] = []
        self.close_calls = 0

    def verify_connectivity(self) -> None:
        self.verify_calls += 1
        if self.failure is not None:
            raise self.failure

    def execute_query(self, query: str, **parameters: Any) -> object:
        self.execute_queries.append((query, parameters))
        return object()

    def close(self) -> None:
        self.close_calls += 1


def _settings(**overrides):
    return Settings(_env_file=None, **overrides)


def test_graph_runtime_defaults_to_disabled_store() -> None:
    store = get_graph_store(_settings())

    assert isinstance(store, DisabledGraphStore)
    assert store.health_check().status == "disabled"


def test_neo4j_runtime_requires_uri_username_and_password() -> None:
    settings = _settings(graph_store="neo4j", neo4j_uri="neo4j://localhost:7687")

    with pytest.raises(
        GraphStoreConfigurationError,
        match="ADAPTIVE_RAG_NEO4J_USERNAME is required for graph_store=neo4j",
    ):
        get_graph_store(settings)


def test_neo4j_runtime_builds_adapter_without_connectivity_check() -> None:
    fake_driver = FakeNeo4jDriver()
    calls: list[tuple[str, tuple[str, str]]] = []

    def driver_factory(uri: str, *, auth: tuple[str, str]) -> FakeNeo4jDriver:
        calls.append((uri, auth))
        return fake_driver

    store = get_graph_store(
        _settings(
            graph_store="neo4j",
            neo4j_uri="neo4j+s://graph.example.test",
            neo4j_username="neo4j",
            neo4j_password="secret-password",
        ),
        driver_factory=driver_factory,
    )

    assert isinstance(store, Neo4jGraphStore)
    assert calls == [
        ("neo4j+s://graph.example.test", ("neo4j", "secret-password")),
    ]
    assert fake_driver.verify_calls == 0

    health = store.health_check()

    assert health.backend == "neo4j"
    assert health.available is True
    assert health.status == "ready"
    assert fake_driver.verify_calls == 1


def test_neo4j_health_maps_auth_error_to_misconfigured_without_secret() -> None:
    store = Neo4jGraphStore(
        driver=FakeNeo4jDriver(failure=AuthError("bad secret-password")),
    )

    health = store.health_check()

    assert health.available is False
    assert health.status == "misconfigured"
    assert health.error_code == "graph_store_misconfigured"
    assert "secret-password" not in repr(health)


def test_neo4j_health_maps_service_unavailable_to_stable_error() -> None:
    store = Neo4jGraphStore(
        driver=FakeNeo4jDriver(failure=ServiceUnavailable("network down")),
    )

    health = store.health_check()

    assert health.available is False
    assert health.status == "unavailable"
    assert health.error_code == "graph_store_unavailable"


def test_neo4j_health_maps_unknown_failures_to_unavailable() -> None:
    store = Neo4jGraphStore(driver=FakeNeo4jDriver(failure=RuntimeError("boom")))

    health = store.health_check()

    assert health.available is False
    assert health.status == "unavailable"
    assert health.error_code == "graph_store_unavailable"


def test_neo4j_close_delegates_to_driver() -> None:
    fake_driver = FakeNeo4jDriver()
    store = Neo4jGraphStore(driver=fake_driver)

    store.close()

    assert fake_driver.close_calls == 1


def test_neo4j_indexing_requires_project_graph_loader() -> None:
    store = Neo4jGraphStore(driver=FakeNeo4jDriver())

    with pytest.raises(
        GraphStoreConfigurationError,
        match="project graph loader is required for neo4j indexing",
    ):
        store.backfill_project_graph(
            project_id=uuid4(),
            source_watermark="chunks:v1",
        )


def test_neo4j_configuration_errors_do_not_include_password() -> None:
    settings = _settings(
        graph_store="neo4j",
        neo4j_uri="neo4j://localhost:7687",
        neo4j_username="neo4j",
        neo4j_password="secret-password",
    )

    def broken_driver_factory(
        uri: str,
        *,
        auth: tuple[str, str],
    ) -> FakeNeo4jDriver:
        raise ValueError(f"failed to create driver for {uri} with {auth[1]}")

    with pytest.raises(GraphStoreUnavailableError) as exc_info:
        get_graph_store(settings, driver_factory=broken_driver_factory)

    assert "secret-password" not in str(exc_info.value)
