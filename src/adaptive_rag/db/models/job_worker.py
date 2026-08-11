"""Operational presence advertised by job-worker processes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.workspace import JSONWithJSONB


class JobWorker(Base):
    """Ephemeral worker presence; attempt leases remain authoritative."""

    __tablename__ = "job_workers"
    __table_args__ = (
        CheckConstraint(
            "length(process_identity) >= 1 AND length(process_identity) <= 128",
            name="job_workers_process_identity_length_check",
        ),
        Index(
            "ix_job_workers_live_heartbeat",
            "heartbeat_at",
            postgresql_where=text("shutdown_at IS NULL"),
            sqlite_where=text("shutdown_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    process_identity: Mapped[str] = mapped_column(String(128), nullable=False)
    application_version: Mapped[str] = mapped_column(String(64), nullable=False)
    supported_queues: Mapped[list[str]] = mapped_column(
        JSONWithJSONB(), nullable=False, default=list, server_default=text("'[]'")
    )
    supported_handlers: Mapped[list[str]] = mapped_column(
        JSONWithJSONB(), nullable=False, default=list, server_default=text("'[]'")
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    draining_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    shutdown_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
