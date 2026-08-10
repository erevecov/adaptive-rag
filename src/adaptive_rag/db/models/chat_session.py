"""Modelo ChatSession: corrida conversacional auditable por proyecto."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.workspace import JSONWithJSONB

CHAT_SESSION_STATUS_VALUES = ("running", "succeeded", "failed", "canceled")


class ChatSession(Base):
    """Sesion de chat que agrupa mensajes, tool calls y retrieval runs."""

    __tablename__ = "chat_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'canceled')",
            name="chat_sessions_status_check",
        ),
        Index("ix_chat_sessions_workspace_created_at", "workspace_id", "created_at"),
        Index(
            "ix_chat_sessions_workspace_user_created_at",
            "workspace_id",
            "user_id",
            "created_at",
        ),
        Index("ix_chat_sessions_workspace_status", "workspace_id", "status"),
        Index(
            "ix_chat_sessions_workspace_user_archived_created_at",
            "workspace_id",
            "user_id",
            "archived_at",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        nullable=False, default="running", server_default="running"
    )
    model_config_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    prompt_version: Mapped[str | None] = mapped_column(nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_is_custom: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(
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
