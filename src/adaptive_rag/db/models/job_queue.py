"""Queue capacity configuration and persistent fair-dispatch cursors."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now


class JobQueue(Base):
    """One configured queue and its database-enforced admission limits."""

    __tablename__ = "job_queues"
    __table_args__ = (
        CheckConstraint(
            "global_concurrency_limit IS NULL OR global_concurrency_limit > 0",
            name="job_queues_global_limit_positive_check",
        ),
        CheckConstraint(
            "workspace_concurrency_limit IS NULL OR workspace_concurrency_limit > 0",
            name="job_queues_workspace_limit_positive_check",
        ),
        CheckConstraint(
            "default_lease_seconds >= 15 AND default_lease_seconds <= 3600",
            name="job_queues_lease_bounds_check",
        ),
        CheckConstraint("version > 0", name="job_queues_version_positive_check"),
    )

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    paused_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paused_by_actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    global_concurrency_limit: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    workspace_concurrency_limit: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    default_lease_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300, server_default="300"
    )
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

class JobQueueWorkspaceState(Base):
    """Persistent round-robin cursor for one queue and workspace/system scope."""

    __tablename__ = "job_queue_workspace_state"
    __table_args__ = (
        CheckConstraint(
            "scope_key = 'system' OR scope_key LIKE 'workspace:%'",
            name="job_queue_workspace_state_scope_key_check",
        ),
    )

    queue_name: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("job_queues.name", ondelete="CASCADE"),
        primary_key=True,
    )
    scope_key: Mapped[str] = mapped_column(String(256), primary_key=True)
    last_claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
