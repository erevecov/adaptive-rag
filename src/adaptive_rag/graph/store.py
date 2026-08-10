"""Graph store contract and deterministic offline implementations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

GraphStoreBackend = Literal["disabled", "neo4j"]
GraphprojectionStatus = Literal[
    "disabled",
    "pending_backfill",
    "indexing",
    "ready",
    "stale",
    "failed",
]
GRAPH_projection_STATUS_VALUES: tuple[GraphprojectionStatus, ...] = (
    "disabled",
    "pending_backfill",
    "indexing",
    "ready",
    "stale",
    "failed",
)


class GraphStoreError(ValueError):
    """Base estable para errores de graph store sin exponer secretos."""

    error_code = "graph_store_error"


class GraphStoreConfigurationError(GraphStoreError):
    """Configuracion invalida o backend no disponible por configuracion."""

    error_code = "graph_store_misconfigured"


class GraphStoreUnavailableError(GraphStoreError):
    """Servicio graph live no disponible."""

    error_code = "graph_store_unavailable"


class GraphStoreQueryError(GraphStoreError):
    """Fallo estable al ejecutar una operacion graph."""

    error_code = "graph_store_query_failed"


@dataclass(frozen=True, slots=True)
class GraphStoreHealth:
    """Resultado serializable del health check de graph store."""

    backend: GraphStoreBackend
    available: bool
    status: str
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class GraphBackfillResult:
    """Resultado de una reconstruccion idempotente por proyecto."""

    workspace_id: UUID
    backend: Literal["neo4j"]
    status: GraphprojectionStatus
    source_watermark: str
    node_count: int | None = None
    relationship_count: int | None = None


@dataclass(frozen=True, slots=True)
class GraphRetrievalResult:
    """Resultado graph routeable antes de rehidratar citations desde Postgres."""

    chunk_id: UUID
    distance: float
    score: float


class GraphRetriever(Protocol):
    """Contrato de consulta graph opt-in con fallback dense externo."""

    def expand_workspace_chunks(
        self,
        *,
        workspace_id: UUID,
        seed_chunk_ids: Sequence[UUID],
        limit: int,
    ) -> tuple[GraphRetrievalResult, ...]:
        """Expande seeds dense contra el grafo derivado de un proyecto."""


class GraphStore(Protocol):
    """Contrato minimo antes de acoplar Neo4j live."""

    backend: GraphStoreBackend

    def health_check(self) -> GraphStoreHealth:
        """Reporta conectividad/configuracion sin exponer credenciales."""

    def backfill_workspace_graph(
        self,
        *,
        workspace_id: UUID,
        source_watermark: str,
    ) -> GraphBackfillResult:
        """Reconstruye el grafo derivado para un proyecto."""

    def delete_workspace_graph(self, *, workspace_id: UUID) -> None:
        """Elimina datos derivados de un proyecto en el backend graph."""


class DisabledGraphStore:
    """Graph store no-op para el default `graph_store=disabled`."""

    backend: GraphStoreBackend = "disabled"

    def health_check(self) -> GraphStoreHealth:
        return GraphStoreHealth(
            backend=self.backend,
            available=False,
            status="disabled",
        )

    def backfill_workspace_graph(
        self,
        *,
        workspace_id: UUID,
        source_watermark: str,
    ) -> GraphBackfillResult:
        raise GraphStoreConfigurationError("graph store is disabled")

    def delete_workspace_graph(self, *, workspace_id: UUID) -> None:
        return None


class FakeGraphStore:
    """Fake determinista sin red para tests de contrato y evals offline."""

    def __init__(self, *, backend: Literal["neo4j"] = "neo4j") -> None:
        self.backend = backend
        self._backfill_requests: list[tuple[UUID, str]] = []
        self._delete_requests: list[UUID] = []

    @property
    def backfill_requests(self) -> tuple[tuple[UUID, str], ...]:
        return tuple(self._backfill_requests)

    @property
    def delete_requests(self) -> tuple[UUID, ...]:
        return tuple(self._delete_requests)

    def health_check(self) -> GraphStoreHealth:
        return GraphStoreHealth(
            backend=self.backend,
            available=True,
            status="ready",
        )

    def backfill_workspace_graph(
        self,
        *,
        workspace_id: UUID,
        source_watermark: str,
    ) -> GraphBackfillResult:
        self._backfill_requests.append((workspace_id, source_watermark))
        return GraphBackfillResult(
            workspace_id=workspace_id,
            backend=self.backend,
            status="ready",
            source_watermark=source_watermark,
        )

    def delete_workspace_graph(self, *, workspace_id: UUID) -> None:
        self._delete_requests.append(workspace_id)


def should_use_dense_fallback(status: str) -> bool:
    """Graph retrieval solo puede usarse cuando la proyeccion esta ready."""

    return status != "ready"
