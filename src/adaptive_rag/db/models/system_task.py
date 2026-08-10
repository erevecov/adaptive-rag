"""Global system task state for in-app scheduled maintenance jobs.

Workspace job queue (`jobs`) is project-scoped and unsuitable for global
provider maintenance. This table tracks last-run and leasing for system-wide
tasks such as daily provider model pricing sync.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.workspace import JSONWithJSONB

# Known task ids (string PKs). Handlers live in adaptive_rag.system_scheduler.
PROVIDER_MODEL_PRICING_SYNC_TASK_ID = "provider_model_pricing_sync"


class SystemTaskState(Base):
    """Lease + last-run row for one global scheduled system task."""

    __tablename__ = "system_task_state"

    task_id: Mapped[str] = mapped_column(primary_key=True)
    interval_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=86_400, server_default="86400"
    )
    last_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_succeeded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_status: Mapped[str | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_report_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    locked_by: Mapped[str | None] = mapped_column(nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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
