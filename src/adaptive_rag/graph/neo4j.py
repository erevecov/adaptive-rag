"""Neo4j-backed graph store adapter."""

from __future__ import annotations

from typing import Protocol, cast
from uuid import UUID

from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, DriverError, Neo4jError, ServiceUnavailable

from adaptive_rag.graph.store import (
    GraphBackfillResult,
    GraphStoreBackend,
    GraphStoreConfigurationError,
    GraphStoreHealth,
    GraphStoreQueryError,
    GraphStoreUnavailableError,
)


class Neo4jDriver(Protocol):
    """Small driver surface this adapter needs for health and lifecycle."""

    def verify_connectivity(self) -> None:
        """Verify that the configured server is reachable."""

    def close(self) -> None:
        """Close network resources owned by the driver."""


class Neo4jDriverFactory(Protocol):
    """Factory matching `GraphDatabase.driver(uri, auth=(user, password))`."""

    def __call__(self, uri: str, *, auth: tuple[str, str]) -> Neo4jDriver:
        """Create a Neo4j driver without forcing connectivity verification."""


class Neo4jGraphStore:
    """Neo4j adapter for health checks before graph indexing is implemented."""

    backend: GraphStoreBackend = "neo4j"

    def __init__(self, *, driver: Neo4jDriver) -> None:
        self._driver = driver

    def health_check(self) -> GraphStoreHealth:
        try:
            self._driver.verify_connectivity()
        except AuthError:
            return GraphStoreHealth(
                backend=self.backend,
                available=False,
                status="misconfigured",
                error_code=GraphStoreConfigurationError.error_code,
            )
        except (ServiceUnavailable, DriverError):
            return GraphStoreHealth(
                backend=self.backend,
                available=False,
                status="unavailable",
                error_code=GraphStoreUnavailableError.error_code,
            )
        except Neo4jError:
            return GraphStoreHealth(
                backend=self.backend,
                available=False,
                status="query_failed",
                error_code=GraphStoreQueryError.error_code,
            )
        except Exception:
            return GraphStoreHealth(
                backend=self.backend,
                available=False,
                status="unavailable",
                error_code=GraphStoreUnavailableError.error_code,
            )

        return GraphStoreHealth(
            backend=self.backend,
            available=True,
            status="ready",
        )

    def backfill_project_graph(
        self,
        *,
        project_id: UUID,
        source_watermark: str,
    ) -> GraphBackfillResult:
        raise GraphStoreQueryError("neo4j graph indexing is not implemented")

    def delete_project_graph(self, *, project_id: UUID) -> None:
        raise GraphStoreQueryError("neo4j graph indexing is not implemented")

    def close(self) -> None:
        self._driver.close()


def default_neo4j_driver_factory(
    uri: str,
    *,
    auth: tuple[str, str],
) -> Neo4jDriver:
    return cast(Neo4jDriver, GraphDatabase.driver(uri, auth=auth))
