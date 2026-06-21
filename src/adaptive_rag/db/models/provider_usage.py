"""Modelo ProviderUsage: usage y costo vinculados a contexto durable."""

from __future__ import annotations

from datetime import datetime
from typing import get_args
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.provider_usage import (
    ProviderCallOutcome,
    ProviderOperation,
    ProviderUsageSource,
)

PROVIDER_USAGE_OPERATION_VALUES: tuple[str, ...] = get_args(ProviderOperation)
PROVIDER_USAGE_STATUS_VALUES: tuple[str, ...] = get_args(ProviderCallOutcome)
PROVIDER_USAGE_SOURCE_VALUES: tuple[str, ...] = get_args(ProviderUsageSource)


class ProviderUsage(Base):
    """Evento de usage/costo de provider para chat, jobs o evals."""

    __tablename__ = "provider_usage"
    __table_args__ = (
        CheckConstraint(
            "operation IN ('chat', 'contextualize', 'embedding', 'rerank', "
            "'eval_judge')",
            name="provider_usage_operation_check",
        ),
        CheckConstraint(
            "status IN ('succeeded', 'failed', 'blocked')",
            name="provider_usage_status_check",
        ),
        CheckConstraint(
            "usage_source IN ('provider_reported', 'estimated', 'unavailable')",
            name="provider_usage_source_check",
        ),
        CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0",
            name="provider_usage_input_tokens_non_negative_check",
        ),
        CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="provider_usage_output_tokens_non_negative_check",
        ),
        CheckConstraint(
            "total_tokens IS NULL OR total_tokens >= 0",
            name="provider_usage_total_tokens_non_negative_check",
        ),
        CheckConstraint(
            "input_count IS NULL OR input_count >= 0",
            name="provider_usage_input_count_non_negative_check",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="provider_usage_latency_ms_non_negative_check",
        ),
        CheckConstraint(
            "estimated_cost_usd IS NULL OR estimated_cost_usd >= 0",
            name="provider_usage_estimated_cost_usd_non_negative_check",
        ),
        Index(
            "ix_provider_usage_project_session_created_at",
            "project_id",
            "session_id",
            "created_at",
        ),
        Index(
            "ix_provider_usage_project_operation_created_at",
            "project_id",
            "operation",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True
    )
    job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    eval_run_id: Mapped[UUID | None] = mapped_column(nullable=True)
    operation: Mapped[str] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(nullable=False)
    model: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    usage_source: Mapped[str] = mapped_column(nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_id: Mapped[str | None] = mapped_column(nullable=True)
    error_type: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
