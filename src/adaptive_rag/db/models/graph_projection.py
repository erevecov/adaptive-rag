"""Estado de readiness/backfill de la proyeccion graph por proyecto."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base

GRAPH_PROJECTION_BACKEND_VALUES = ("neo4j",)
GRAPH_PROJECTION_STATUS_VALUES = (
    "disabled",
    "pending_backfill",
    "indexing",
    "ready",
    "stale",
    "failed",
)
DEFAULT_GRAPH_SCHEMA_VERSION = "graph-store-v1"
DEFAULT_GRAPH_EXTRACTOR_VERSION = "graph-extractor-v1"


class GraphProjection(Base):
    """Readiness de un indice graph derivado y reconstruible desde Postgres."""

    __tablename__ = "graph_projections"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "backend",
            name="uq_graph_projections_project_backend",
        ),
        CheckConstraint(
            "backend IN ('neo4j')",
            name="graph_projections_backend_check",
        ),
        CheckConstraint(
            "status IN ("
            + ", ".join(f"'{status}'" for status in GRAPH_PROJECTION_STATUS_VALUES)
            + ")",
            name="graph_projections_status_check",
        ),
        Index("ix_graph_projections_project_status", "project_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    backend: Mapped[str] = mapped_column(
        nullable=False, default="neo4j", server_default="neo4j"
    )
    status: Mapped[str] = mapped_column(
        nullable=False, default="disabled", server_default="disabled"
    )
    source_watermark: Mapped[str | None] = mapped_column(nullable=True)
    schema_version: Mapped[str] = mapped_column(
        nullable=False,
        default=DEFAULT_GRAPH_SCHEMA_VERSION,
        server_default=DEFAULT_GRAPH_SCHEMA_VERSION,
    )
    extractor_version: Mapped[str] = mapped_column(
        nullable=False,
        default=DEFAULT_GRAPH_EXTRACTOR_VERSION,
        server_default=DEFAULT_GRAPH_EXTRACTOR_VERSION,
    )
    last_indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
