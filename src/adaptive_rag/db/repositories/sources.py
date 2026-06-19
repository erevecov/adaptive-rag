"""Repository de sources con aislamiento por proyecto."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Source
from adaptive_rag.db.repositories.filters import SourceFilters


class SourceRepository:
    """Acceso a sources siempre filtrado por `project_id`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        project_id: UUID,
        source_type: str,
        external_id: str,
        tags: Sequence[str] | None = None,
        extra_metadata: Mapping[str, Any] | None = None,
    ) -> Source:
        source = Source(
            project_id=project_id,
            source_type=source_type,
            external_id=external_id,
            tags=list(tags) if tags is not None else None,
            extra_metadata=dict(extra_metadata) if extra_metadata is not None else None,
        )
        self._session.add(source)
        self._session.flush()
        return source

    def list(
        self,
        *,
        project_id: UUID,
        filters: SourceFilters | None = None,
    ) -> list[Source]:
        active_filters = filters or SourceFilters()
        statement = select(Source).where(Source.project_id == project_id)

        if active_filters.source_type is not None:
            statement = statement.where(
                Source.source_type == active_filters.source_type
            )
        if active_filters.external_id is not None:
            statement = statement.where(
                Source.external_id == active_filters.external_id
            )
        if active_filters.created_at_from is not None:
            statement = statement.where(
                Source.created_at >= active_filters.created_at_from
            )
        if active_filters.created_at_to is not None:
            statement = statement.where(
                Source.created_at <= active_filters.created_at_to
            )

        statement = statement.order_by(Source.created_at, Source.external_id)
        sources = list(self._session.scalars(statement))

        if active_filters.tag is None:
            return sources

        return [
            source
            for source in sources
            if source.tags is not None and active_filters.tag in source.tags
        ]

    def get(self, *, project_id: UUID, source_id: UUID) -> Source | None:
        statement = select(Source).where(
            Source.id == source_id,
            Source.project_id == project_id,
        )
        return self._session.scalars(statement).one_or_none()

    def get_by_identity(
        self,
        *,
        project_id: UUID,
        source_type: str,
        external_id: str,
    ) -> Source | None:
        statement = select(Source).where(
            Source.project_id == project_id,
            Source.source_type == source_type,
            Source.external_id == external_id,
        )
        return self._session.scalars(statement).one_or_none()
