"""Modelo RetrievedChunk: chunk recuperado y citation persistida."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.project import JSONWithJSONB


class RetrievedChunk(Base):
    """Resultado citable de una corrida de retrieval."""

    __tablename__ = "retrieved_chunks"
    __table_args__ = (
        UniqueConstraint(
            "retrieval_run_id",
            "rank",
            name="uq_retrieved_chunks_retrieval_run_rank",
        ),
        CheckConstraint("rank > 0", name="retrieved_chunks_rank_positive_check"),
        Index(
            "ix_retrieved_chunks_project_retrieval_run_rank",
            "project_id",
            "retrieval_run_id",
            "rank",
        ),
        Index("ix_retrieved_chunks_project_chunk", "project_id", "chunk_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    retrieval_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("retrieval_runs.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[UUID] = mapped_column(ForeignKey("chunks.id"), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    dense_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sparse_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rerank_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    citation_json: Mapped[dict[str, Any]] = mapped_column(
        JSONWithJSONB(none_as_null=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
