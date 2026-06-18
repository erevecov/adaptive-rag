"""Modelo Source: identidad de ingestion asociada a un proyecto."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.project import JSONWithJSONB


class Source(Base):
    """Source de ingestion (web, file, etc.) perteneciente a un proyecto."""

    __tablename__ = "sources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(nullable=False)
    external_id: Mapped[str] = mapped_column(nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(JSONWithJSONB(), nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
