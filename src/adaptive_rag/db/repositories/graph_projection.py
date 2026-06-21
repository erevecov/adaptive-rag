"""Repository de readiness/backfill de proyeccion graph."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import GraphProjection
from adaptive_rag.db.models.graph_projection import (
    DEFAULT_GRAPH_EXTRACTOR_VERSION,
    DEFAULT_GRAPH_SCHEMA_VERSION,
)


class GraphProjectionRepository:
    """Acceso al estado graph por proyecto con transaccion controlada por caller."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(
        self,
        *,
        project_id: UUID,
        backend: str = "neo4j",
    ) -> GraphProjection | None:
        statement = select(GraphProjection).where(
            GraphProjection.project_id == project_id,
            GraphProjection.backend == backend,
        )
        return self._session.scalars(statement).one_or_none()

    def ensure(
        self,
        *,
        project_id: UUID,
        backend: str = "neo4j",
    ) -> GraphProjection:
        projection = self.get(project_id=project_id, backend=backend)
        if projection is not None:
            return projection
        projection = GraphProjection(project_id=project_id, backend=backend)
        self._session.add(projection)
        self._session.flush()
        return projection

    def mark_pending_backfill(
        self,
        *,
        project_id: UUID,
        source_watermark: str,
        schema_version: str = DEFAULT_GRAPH_SCHEMA_VERSION,
        extractor_version: str = DEFAULT_GRAPH_EXTRACTOR_VERSION,
    ) -> GraphProjection:
        projection = self.ensure(project_id=project_id)
        projection.status = "pending_backfill"
        projection.source_watermark = source_watermark
        projection.schema_version = schema_version
        projection.extractor_version = extractor_version
        projection.last_indexed_at = None
        self._clear_error(projection)
        self._session.flush()
        return projection

    def mark_indexing(self, *, project_id: UUID) -> GraphProjection:
        projection = self.ensure(project_id=project_id)
        projection.status = "indexing"
        self._clear_error(projection)
        self._session.flush()
        return projection

    def mark_ready(
        self,
        *,
        project_id: UUID,
        source_watermark: str,
        indexed_at: datetime,
    ) -> GraphProjection:
        projection = self.ensure(project_id=project_id)
        projection.status = "ready"
        projection.source_watermark = source_watermark
        projection.last_indexed_at = indexed_at
        self._clear_error(projection)
        self._session.flush()
        return projection

    def mark_stale(
        self,
        *,
        project_id: UUID,
        source_watermark: str,
    ) -> GraphProjection:
        projection = self.ensure(project_id=project_id)
        projection.status = "stale"
        projection.source_watermark = source_watermark
        self._session.flush()
        return projection

    def mark_failed(
        self,
        *,
        project_id: UUID,
        error_code: str,
        error_message: str,
    ) -> GraphProjection:
        projection = self.ensure(project_id=project_id)
        projection.status = "failed"
        projection.error_code = error_code
        projection.error_message = error_message
        self._session.flush()
        return projection

    @staticmethod
    def _clear_error(projection: GraphProjection) -> None:
        projection.error_code = None
        projection.error_message = None
