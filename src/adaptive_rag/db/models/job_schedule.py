"""Durable five-field cron schedules that enqueue normal jobs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.workspace import JSONWithJSONB

JOB_MISFIRE_POLICY_VALUES = ("skip", "run_once", "catch_up")


class JobSchedule(Base):
    """Versioned schedule definition; occurrences become regular jobs."""

    __tablename__ = "job_schedules"
    __table_args__ = (
        CheckConstraint(
            "(scope = 'workspace' AND workspace_id IS NOT NULL) OR "
            "(scope = 'system' AND workspace_id IS NULL)",
            name="job_schedules_scope_workspace_check",
        ),
        CheckConstraint(
            "misfire_policy IN ('skip', 'run_once', 'catch_up')",
            name="job_schedules_misfire_policy_check",
        ),
        CheckConstraint(
            "max_catch_up >= 1 AND max_catch_up <= 100",
            name="job_schedules_max_catch_up_bounds_check",
        ),
        CheckConstraint(
            "handler_version > 0",
            name="job_schedules_handler_version_positive_check",
        ),
        CheckConstraint(
            "priority >= -1000 AND priority <= 1000",
            name="job_schedules_priority_bounds_check",
        ),
        CheckConstraint("version > 0", name="job_schedules_version_positive_check"),
        Index(
            "ix_job_schedules_due",
            "next_run_at",
            postgresql_where=text("paused_at IS NULL AND archived_at IS NULL"),
            sqlite_where=text("paused_at IS NULL AND archived_at IS NULL"),
        ),
        Index("ix_job_schedules_workspace_created", "workspace_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    scope: Mapped[str] = mapped_column(
        String(16), nullable=False, default="workspace", server_default="workspace"
    )
    workspace_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    queue_name: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("job_queues.name", ondelete="RESTRICT"),
        nullable=False,
    )
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    handler_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(
        JSONWithJSONB(), nullable=False, default=dict, server_default=text("'{}'")
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    concurrency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cron_expression: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False)
    misfire_policy: Mapped[str] = mapped_column(
        String(16), nullable=False, default="run_once", server_default="run_once"
    )
    max_catch_up: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    paused_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_actor_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_by_actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by_actor_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_by_actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
        onupdate=func.now(),
    )
