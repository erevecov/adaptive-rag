"""Append-only audit events for workspace and system jobs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.workspace import JSONWithJSONB

JOB_EVENT_TYPE_VALUES = (
    "created",
    "queued",
    "leased",
    "progress",
    "completed",
    "completed_after_cancel_request",
    "failed_attempt",
    "retry_scheduled",
    "blocked",
    "unblocked",
    "dead_lettered",
    "cancel_requested",
    "cancelled",
    "expired",
    "retried",
    "released",
    "scheduled",
    "run_now",
)


class JobEvent(Base):
    """Bounded, redacted audit event associated with one logical job."""

    __tablename__ = "job_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ("
            + ", ".join(f"'{value}'" for value in JOB_EVENT_TYPE_VALUES)
            + ")",
            name="job_events_event_type_check",
        ),
        CheckConstraint(
            "(scope = 'workspace' AND workspace_id IS NOT NULL) OR "
            "(scope = 'system' AND workspace_id IS NULL)",
            name="job_events_scope_workspace_check",
        ),
        Index(
            "ix_job_events_workspace_job_created_at",
            "workspace_id",
            "job_id",
            "created_at",
        ),
        Index("ix_job_events_workspace_event_type", "workspace_id", "event_type"),
        Index("ix_job_events_job_created_at", "job_id", "created_at", "id"),
        Index("ix_job_events_attempt_id", "attempt_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    scope: Mapped[str] = mapped_column(
        String(16), nullable=False, default="workspace", server_default="workspace"
    )
    workspace_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("job_attempts.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    actor_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
