"""Models for global runtime slot defaults and chat model pool."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.project import JSONWithJSONB

RUNTIME_SLOT_VALUES = (
    "chat",
    "dense_embedding",
    "sparse_embedding",
    "rerank",
    "contextualization",
)


class RuntimeSlotDefault(Base):
    """Global default model selection for a fixed runtime slot."""

    __tablename__ = "runtime_slot_defaults"
    __table_args__ = (
        CheckConstraint(
            "slot IN ('chat', 'dense_embedding', 'sparse_embedding', "
            "'rerank', 'contextualization')",
            name="runtime_slot_defaults_slot_check",
        ),
    )

    slot: Mapped[str] = mapped_column(primary_key=True)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("provider_connections.connection_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_id: Mapped[str] = mapped_column(nullable=False)
    parameters_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
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


class GlobalChatModel(Base):
    """Enabled global chat model, with at most one repository-enforced default."""

    __tablename__ = "global_chat_models"
    __table_args__ = (
        Index("ix_global_chat_models_default", "is_default"),
    )

    connection_id: Mapped[str] = mapped_column(
        ForeignKey("provider_connections.connection_id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_id: Mapped[str] = mapped_column(primary_key=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    parameters_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
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


class ProjectRuntimeSlotOverride(Base):
    """Project-scoped runtime slot override without secret values."""

    __tablename__ = "project_runtime_slot_overrides"
    __table_args__ = (
        CheckConstraint(
            "slot IN ('chat', 'dense_embedding', 'sparse_embedding', "
            "'rerank', 'contextualization')",
            name="project_runtime_slot_overrides_slot_check",
        ),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    slot: Mapped[str] = mapped_column(primary_key=True)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("provider_connections.connection_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_id: Mapped[str] = mapped_column(nullable=False)
    parameters_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
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


class ProjectChatModel(Base):
    """Project-scoped chat model pool entry without secret values."""

    __tablename__ = "project_chat_models"
    __table_args__ = (
        Index("ix_project_chat_models_project_default", "project_id", "is_default"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("provider_connections.connection_id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_id: Mapped[str] = mapped_column(primary_key=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    parameters_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
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
