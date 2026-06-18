"""Filtros tipados para repositories de dominio."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SourceFilters:
    """Filtros soportados para listar sources dentro de un proyecto."""

    source_type: str | None = None
    external_id: str | None = None
    tag: str | None = None
    created_at_from: datetime | None = None
    created_at_to: datetime | None = None


@dataclass(frozen=True, slots=True)
class DocumentFilters:
    """Filtros soportados para listar documents dentro de un proyecto."""

    source_id: UUID | None = None
    stable_id: str | None = None
    created_at_from: datetime | None = None
    created_at_to: datetime | None = None

