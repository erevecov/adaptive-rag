"""Neo4j-backed graph store adapter."""

from __future__ import annotations

from typing import Any, Protocol, cast
from uuid import UUID

from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, DriverError, Neo4jError, ServiceUnavailable

from adaptive_rag.graph.indexer import ProjectGraphLoader
from adaptive_rag.graph.store import (
    GraphBackfillResult,
    GraphStoreBackend,
    GraphStoreConfigurationError,
    GraphStoreHealth,
    GraphStoreQueryError,
    GraphStoreUnavailableError,
)


class Neo4jDriver(Protocol):
    """Small driver surface this adapter needs for health and indexing."""

    def verify_connectivity(self) -> None:
        """Verify that the configured server is reachable."""

    def execute_query(self, query: str, **parameters: Any) -> object:
        """Execute a Cypher query with named parameters."""

    def close(self) -> None:
        """Close network resources owned by the driver."""


class Neo4jDriverFactory(Protocol):
    """Factory matching `GraphDatabase.driver(uri, auth=(user, password))`."""

    def __call__(self, uri: str, *, auth: tuple[str, str]) -> Neo4jDriver:
        """Create a Neo4j driver without forcing connectivity verification."""


class Neo4jGraphStore:
    """Neo4j adapter for health checks and project graph indexing."""

    backend: GraphStoreBackend = "neo4j"

    def __init__(
        self,
        *,
        driver: Neo4jDriver,
        project_graph_loader: ProjectGraphLoader | None = None,
    ) -> None:
        self._driver = driver
        self._project_graph_loader = project_graph_loader

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
        if self._project_graph_loader is None:
            raise GraphStoreConfigurationError(
                "project graph loader is required for neo4j indexing"
            )

        try:
            graph = self._project_graph_loader(project_id)
        except (GraphStoreConfigurationError, GraphStoreQueryError):
            raise
        except Exception as exc:
            raise GraphStoreQueryError(
                "failed to load project graph source data"
            ) from exc

        self.delete_project_graph(project_id=project_id)
        self._execute_query(
            _UPSERT_PROJECT_QUERY,
            project=graph.project,
            source_watermark=source_watermark,
        )
        self._execute_query(_UPSERT_SOURCES_QUERY, sources=list(graph.sources))
        self._execute_query(_UPSERT_DOCUMENTS_QUERY, documents=list(graph.documents))
        self._execute_query(
            _UPSERT_DOCUMENT_VERSIONS_QUERY,
            document_versions=list(graph.document_versions),
        )
        self._execute_query(_UPSERT_CHUNKS_QUERY, chunks=list(graph.chunks))
        self._execute_query(
            _UPSERT_CHUNK_LINKS_QUERY,
            chunk_links=list(graph.chunk_links),
        )
        return GraphBackfillResult(
            project_id=project_id,
            backend="neo4j",
            status="ready",
            source_watermark=source_watermark,
        )

    def delete_project_graph(self, *, project_id: UUID) -> None:
        self._execute_query(_DELETE_PROJECT_GRAPH_QUERY, project_id=str(project_id))

    def close(self) -> None:
        self._driver.close()

    def _execute_query(self, query: str, **parameters: Any) -> None:
        try:
            self._driver.execute_query(query, **parameters)
        except (ServiceUnavailable, DriverError) as exc:
            raise GraphStoreUnavailableError("neo4j graph store unavailable") from exc
        except Neo4jError as exc:
            raise GraphStoreQueryError("neo4j graph query failed") from exc
        except Exception as exc:
            raise GraphStoreQueryError("neo4j graph query failed") from exc


def default_neo4j_driver_factory(
    uri: str,
    *,
    auth: tuple[str, str],
) -> Neo4jDriver:
    return cast(Neo4jDriver, GraphDatabase.driver(uri, auth=auth))


_DELETE_PROJECT_GRAPH_QUERY = """
MATCH (n:AdaptiveRagGraph {project_id: $project_id})
DETACH DELETE n
"""

_UPSERT_PROJECT_QUERY = """
WITH $project AS project
MERGE (p:AdaptiveRagGraph:AdaptiveRagProject {id: project.id})
SET p += project,
    p.source_watermark = $source_watermark
"""

_UPSERT_SOURCES_QUERY = """
UNWIND $sources AS source
MERGE (s:AdaptiveRagGraph:AdaptiveRagSource {id: source.id})
SET s += source
WITH source, s
MATCH (p:AdaptiveRagProject {id: source.project_id})
MERGE (p)-[:HAS_SOURCE]->(s)
"""

_UPSERT_DOCUMENTS_QUERY = """
UNWIND $documents AS document
MERGE (d:AdaptiveRagGraph:AdaptiveRagDocument {id: document.id})
SET d += document
WITH document, d
MATCH (s:AdaptiveRagSource {id: document.source_id})
MERGE (s)-[:HAS_DOCUMENT]->(d)
"""

_UPSERT_DOCUMENT_VERSIONS_QUERY = """
UNWIND $document_versions AS version
MERGE (v:AdaptiveRagGraph:AdaptiveRagDocumentVersion {id: version.id})
SET v += version
WITH version, v
MATCH (d:AdaptiveRagDocument {id: version.document_id})
MERGE (d)-[:HAS_VERSION]->(v)
"""

_UPSERT_CHUNKS_QUERY = """
UNWIND $chunks AS chunk
MERGE (c:AdaptiveRagGraph:AdaptiveRagChunk {id: chunk.id})
SET c += chunk
WITH chunk, c
MATCH (v:AdaptiveRagDocumentVersion {id: chunk.document_version_id})
MERGE (v)-[:HAS_CHUNK]->(c)
"""

_UPSERT_CHUNK_LINKS_QUERY = """
UNWIND $chunk_links AS link
MATCH (left:AdaptiveRagChunk {id: link.from_chunk_id})
MATCH (right:AdaptiveRagChunk {id: link.to_chunk_id})
MERGE (left)-[:NEXT_CHUNK]->(right)
"""
