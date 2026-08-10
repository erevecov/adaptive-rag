"""Modelo JobEvent: auditoria append-only de jobs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.workspace import JSONWithJSONB

JOB_EVENT_TYPE_VALUES = (
    "created",
    "leased",
    "completed",
    "failed_attempt",
    "blocked",
    "dead_lettered",
    "released",
    "retried",
)


class JobEvent(Base):
    """Evento append-only asociado a un job y a su proyecto."""

    __tablename__ = "job_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ("
            "'created', 'leased', 'completed', 'failed_attempt', "
            "'blocked', 'dead_lettered', 'released', 'retried'"
            ")",
            name="job_events_event_type_check",
        ),
        Index(
            "ix_job_events_workspace_job_created_at",
            "workspace_id",
            "job_id",
            "created_at",
        ),
        Index("ix_job_events_workspace_event_type", "workspace_id", "event_type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
