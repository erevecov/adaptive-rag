"""Runtime factory for routeable graph store backends."""

from __future__ import annotations

from adaptive_rag.config.settings import Settings, get_settings
from adaptive_rag.graph.neo4j import (
    Neo4jDriverFactory,
    Neo4jGraphStore,
    default_neo4j_driver_factory,
)
from adaptive_rag.graph.store import (
    DisabledGraphStore,
    GraphStore,
    GraphStoreConfigurationError,
    GraphStoreError,
    GraphStoreUnavailableError,
)


def get_graph_store(
    settings: Settings | None = None,
    *,
    driver_factory: Neo4jDriverFactory | None = None,
) -> GraphStore:
    runtime_settings = settings or get_settings()
    if runtime_settings.graph_store == "disabled":
        return DisabledGraphStore()

    uri, username, password = _require_neo4j_settings(runtime_settings)
    active_driver_factory = driver_factory or default_neo4j_driver_factory
    try:
        driver = active_driver_factory(uri, auth=(username, password))
    except GraphStoreError:
        raise
    except Exception as exc:
        raise GraphStoreUnavailableError(
            "failed to initialize neo4j graph store"
        ) from exc
    return Neo4jGraphStore(driver=driver)


def _require_neo4j_settings(settings: Settings) -> tuple[str, str, str]:
    if not settings.neo4j_uri:
        raise GraphStoreConfigurationError(
            "ADAPTIVE_RAG_NEO4J_URI is required for graph_store=neo4j"
        )
    if not settings.neo4j_username:
        raise GraphStoreConfigurationError(
            "ADAPTIVE_RAG_NEO4J_USERNAME is required for graph_store=neo4j"
        )
    if settings.neo4j_password is None:
        raise GraphStoreConfigurationError(
            "ADAPTIVE_RAG_NEO4J_PASSWORD is required for graph_store=neo4j"
        )
    return (
        settings.neo4j_uri,
        settings.neo4j_username,
        settings.neo4j_password.get_secret_value(),
    )
