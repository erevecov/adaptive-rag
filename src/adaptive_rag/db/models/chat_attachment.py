"""Modelo ChatAttachment: archivo adjunto a un mensaje de chat (design §2)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now

CHAT_ATTACHMENT_KIND_VALUES = ("image", "document")
CHAT_ATTACHMENT_STATUS_VALUES = ("ready", "failed")


class ChatAttachment(Base):
    """Adjunto subido por un usuario para incluirlo en un turno de chat."""

    __tablename__ = "chat_attachments"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('image', 'document')",
            name="chat_attachments_kind_check",
        ),
        CheckConstraint(
            "status IN ('ready', 'failed')",
            name="chat_attachments_status_check",
        ),
        Index("ix_chat_attachments_workspace_user", "workspace_id", "user_id"),
        Index("ix_chat_attachments_session", "session_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    mime: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ready", server_default="ready"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
