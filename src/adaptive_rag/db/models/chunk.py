"""Modelo Chunk: fragmento de texto con embedding denso y linaje."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.project import JSONWithJSONB

# Dimension del embedding denso baseline (Qwen). Sin HNSW: dense exacto.
EMBEDDING_DIMENSIONS = 1024


class Chunk(Base):
    """Fragmento de texto de un document version con embedding denso.

    `char_start`/`char_end` son offsets sobre
    `document_versions.normalized_text`. El linaje (`ordinal`,
    `prev_chunk_id`, `next_chunk_id`) permite reconstruir el orden local.
    """

    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "ordinal",
            name="uq_chunks_document_version_ordinal",
        ),
        CheckConstraint("ordinal >= 0", name="chunks_ordinal_non_negative_check"),
        CheckConstraint(
            "char_start >= 0", name="chunks_char_start_non_negative_check"
        ),
        CheckConstraint("char_end > char_start", name="chunks_char_range_check"),
        CheckConstraint(
            "token_count IS NULL OR token_count >= 0",
            name="chunks_token_count_non_negative_check",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prev_chunk_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True
    )
    next_chunk_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True
    )
    section_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    chunker_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    embedding_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    # Campo reservado para contextual retrieval (no implementado en v1).
    contextual_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Embedding denso baseline: vector(1024) en Postgres/pgvector.
    # El variant JSON permite que los tests unitarios en SQLite persistan listas;
    # la dimension exacta se valida en integracion contra pgvector.
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS).with_variant(JSONWithJSONB(), "sqlite"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
