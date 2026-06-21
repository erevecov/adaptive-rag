"""Modelo RetrievalRun: ejecucion de retrieval dentro de una sesion."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.project import JSONWithJSONB


class RetrievalRun(Base):
    """Corrida de retrieval asociada a chat y opcionalmente a una tool call."""

    __tablename__ = "retrieval_runs"
    __table_args__ = (
        CheckConstraint("top_k > 0", name="retrieval_runs_top_k_positive_check"),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="retrieval_runs_latency_ms_non_negative_check",
        ),
        Index(
            "ix_retrieval_runs_project_session_created_at",
            "project_id",
            "session_id",
            "created_at",
        ),
        Index("ix_retrieval_runs_project_strategy", "project_id", "strategy"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    tool_call_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tool_calls.id", ondelete="SET NULL"), nullable=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    strategy: Mapped[str] = mapped_column(nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    used_rerank: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    filters_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
