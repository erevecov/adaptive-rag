"""Modelo DocumentVersion: version parseada de un documento, ancla de citas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

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


class DocumentVersion(Base):
    """Version parseada de un documento.

    `normalized_text` es el texto fuente sobre el que se calculan los
    offsets (`char_start`, `char_end`) de los chunks. Re-parsear crea una
    version nueva; las versiones anteriores siguen anclando sus chunks.
    """

    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_document_versions_document_version_number",
        ),
        CheckConstraint(
            "version_number > 0",
            name="document_versions_version_number_positive_check",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(nullable=False)
    index_fingerprint: Mapped[str] = mapped_column(nullable=False)
    parser_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    extraction_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
