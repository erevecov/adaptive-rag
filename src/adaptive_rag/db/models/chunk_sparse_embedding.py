"""Modelo ChunkSparseEmbedding: sparse embeddings opcionales y aislados."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.project import JSONWithJSONB


class ChunkSparseEmbedding(Base):
    """Sparse embeddings de un chunk (modo experimental `dense_sparse`).

    Tabla separada y opcional (decision D4): los proyectos dense-only no
    necesitan filas aca. Cada fila preserva metadata de reproducibilidad
    (`input_hash`, `index_fingerprint`).
    """

    __tablename__ = "chunk_sparse_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "chunk_id",
            "index_fingerprint",
            name="uq_chunk_sparse_embeddings_chunk_fingerprint",
        ),
        CheckConstraint(
            "sparse_size >= 0",
            name="chunk_sparse_embeddings_sparse_size_non_negative_check",
        ),
        Index(
            "ix_chunk_sparse_embeddings_sparse_indices",
            "sparse_indices",
            postgresql_using="gin",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    chunk_id: Mapped[UUID] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sparse_indices: Mapped[list[int]] = mapped_column(
        JSONWithJSONB(), nullable=False
    )
    sparse_values: Mapped[list[float]] = mapped_column(
        JSONWithJSONB(), nullable=False
    )
    sparse_tokens: Mapped[list[str] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    sparse_size: Mapped[int] = mapped_column(Integer, nullable=False)
    input_hash: Mapped[str] = mapped_column(nullable=False)
    index_fingerprint: Mapped[str] = mapped_column(nullable=False)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
