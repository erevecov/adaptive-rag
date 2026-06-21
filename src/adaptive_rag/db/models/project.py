"""Modelo Project: registro de proyecto que define aislamiento y retrieval."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, TypeDecorator

from adaptive_rag.db.base import Base


class JSONWithJSONB(TypeDecorator[Any]):
    """Usa JSONB en Postgres y JSON generico en otros dialectos (SQLite)."""

    impl = JSON
    cache_ok = True

    def __init__(self, *, none_as_null: bool = False) -> None:
        super().__init__()
        self.none_as_null = none_as_null

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB(none_as_null=self.none_as_null))
        return dialect.type_descriptor(JSON(none_as_null=self.none_as_null))


class Project(Base):
    """Registro de proyecto que aísla todos los datos RAG."""

    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "embedding_mode IN ('dense', 'dense_sparse')",
            name="projects_embedding_mode_check",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(nullable=False)
    embedding_mode: Mapped[str] = mapped_column(
        nullable=False, default="dense", server_default="dense"
    )
    retrieval_contextualization_enabled: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default="true"
    )
    budget_config_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
