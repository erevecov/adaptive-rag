"""Canonical logical record for workspace and system background jobs."""

from __future__ import annotations

from datetime import UTC, datetime
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
from adaptive_rag.db.models.workspace import JSONWithJSONB

JOB_SCOPE_VALUES = ("workspace", "system")
JOB_STATUS_VALUES = (
    "queued",
    "running",
    "succeeded",
    "blocked",
    "dead_letter",
    "cancelled",
)
OPEN_JOB_STATUS_VALUES = ("queued", "running", "blocked")


def utc_now() -> datetime:
    return datetime.now(UTC)


class Job(Base):
    """Durable logical job whose attempts are leased independently."""

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'blocked', "
            "'dead_letter', 'cancelled')",
            name="jobs_status_check",
        ),
        CheckConstraint(
            "(scope = 'workspace' AND workspace_id IS NOT NULL) OR "
            "(scope = 'system' AND workspace_id IS NULL)",
            name="jobs_scope_workspace_check",
        ),
        CheckConstraint("attempts >= 0", name="jobs_attempts_non_negative_check"),
        CheckConstraint("max_attempts > 0", name="jobs_max_attempts_positive_check"),
        CheckConstraint(
            "attempt_count >= 0", name="jobs_attempt_count_non_negative_check"
        ),
        CheckConstraint(
            "retry_count >= 0", name="jobs_retry_count_non_negative_check"
        ),
        CheckConstraint(
            "max_retries >= 0 AND max_retries <= 25",
            name="jobs_max_retries_bounds_check",
        ),
        CheckConstraint(
            "handler_version > 0", name="jobs_handler_version_positive_check"
        ),
        CheckConstraint(
            "priority >= -1000 AND priority <= 1000",
            name="jobs_priority_bounds_check",
        ),
        CheckConstraint("version > 0", name="jobs_version_positive_check"),
        CheckConstraint(
            "(idempotency_key IS NULL AND idempotency_fingerprint IS NULL) OR "
            "(idempotency_key IS NOT NULL AND idempotency_fingerprint IS NOT NULL)",
            name="jobs_idempotency_fingerprint_check",
        ),
        Index(
            "ix_jobs_workspace_status_run_after_priority",
            "workspace_id",
            "status",
            "run_after",
            "priority",
        ),
        Index("ix_jobs_workspace_locked_until", "workspace_id", "locked_until"),
        Index("ix_jobs_workspace_created_at", "workspace_id", "created_at"),
        Index(
            "ix_jobs_queue_status_run_after_priority",
            "queue_name",
            "status",
            "run_after",
            "priority",
            "created_at",
            "id",
        ),
        Index("ix_jobs_current_attempt_id", "current_attempt_id"),
        Index("ix_jobs_schedule_scheduled_for", "schedule_id", "scheduled_for"),
        Index(
            "uq_jobs_workspace_open_idempotency",
            "workspace_id",
            "job_type",
            "handler_version",
            "idempotency_key",
            unique=True,
            postgresql_where=text(
                "scope = 'workspace' AND idempotency_key IS NOT NULL "
                "AND status IN ('queued', 'running', 'blocked')"
            ),
            sqlite_where=text(
                "scope = 'workspace' AND idempotency_key IS NOT NULL "
                "AND status IN ('queued', 'running', 'blocked')"
            ),
        ),
        Index(
            "uq_jobs_system_open_idempotency",
            "job_type",
            "handler_version",
            "idempotency_key",
            unique=True,
            postgresql_where=text(
                "scope = 'system' AND idempotency_key IS NOT NULL "
                "AND status IN ('queued', 'running', 'blocked')"
            ),
            sqlite_where=text(
                "scope = 'system' AND idempotency_key IS NOT NULL "
                "AND status IN ('queued', 'running', 'blocked')"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    scope: Mapped[str] = mapped_column(
        String(16), nullable=False, default="workspace", server_default="workspace"
    )
    workspace_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )
    queue_name: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("job_queues.name", ondelete="RESTRICT"),
        nullable=False,
        default="ingestion",
        server_default="ingestion",
    )
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    handler_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="queued", server_default="queued"
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(
        JSONWithJSONB(), nullable=False, default=dict, server_default=text("'{}'")
    )
    result_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_fingerprint: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default="3"
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    max_retries: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2, server_default="2"
    )
    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    current_attempt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("job_attempts.id", ondelete="SET NULL"), nullable=True
    )
    schedule_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("job_schedules.id", ondelete="SET NULL"), nullable=True
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    concurrency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancellation_requested_by_actor_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    cancellation_requested_by_actor_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )

    # Compatibility columns retained while old API/CLI surfaces delegate.
    locked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
