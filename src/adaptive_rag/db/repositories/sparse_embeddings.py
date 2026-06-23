"""Repository de sparse embeddings por chunk."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import (
    Chunk,
    ChunkSparseEmbedding,
    Document,
    DocumentVersion,
)

if TYPE_CHECKING:
    from adaptive_rag.embeddings.sparse import SparseEmbeddingVector


class SparseEmbeddingRepository:
    """Acceso a sparse embeddings con validacion de pertenencia por proyecto."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_current(
        self,
        *,
        project_id: UUID,
        chunk_id: UUID,
        index_fingerprint: str,
    ) -> ChunkSparseEmbedding | None:
        if not self._chunk_belongs_to_project(project_id=project_id, chunk_id=chunk_id):
            return None
        statement = select(ChunkSparseEmbedding).where(
            ChunkSparseEmbedding.chunk_id == chunk_id,
            ChunkSparseEmbedding.index_fingerprint == index_fingerprint,
        )
        return self._session.scalars(statement).one_or_none()

    def upsert_current(
        self,
        *,
        project_id: UUID,
        chunk_id: UUID,
        vector: SparseEmbeddingVector,
        input_hash: str,
        index_fingerprint: str,
        extra_metadata: Mapping[str, Any] | None = None,
    ) -> ChunkSparseEmbedding:
        if not self._chunk_belongs_to_project(project_id=project_id, chunk_id=chunk_id):
            raise ValueError("chunk does not belong to project")

        self._session.execute(
            delete(ChunkSparseEmbedding).where(
                ChunkSparseEmbedding.chunk_id == chunk_id,
                ChunkSparseEmbedding.index_fingerprint != index_fingerprint,
            )
        )
        row = self._session.scalars(
            select(ChunkSparseEmbedding).where(
                ChunkSparseEmbedding.chunk_id == chunk_id,
                ChunkSparseEmbedding.index_fingerprint == index_fingerprint,
            )
        ).one_or_none()
        if row is None:
            row = ChunkSparseEmbedding(
                chunk_id=chunk_id,
                sparse_indices=[],
                sparse_values=[],
                sparse_size=0,
                input_hash=input_hash,
                index_fingerprint=index_fingerprint,
            )
            self._session.add(row)

        row.sparse_indices = list(vector.indices)
        row.sparse_values = list(vector.values)
        row.sparse_tokens = list(vector.tokens) if vector.tokens is not None else None
        row.sparse_size = vector.sparse_size
        row.input_hash = input_hash
        row.index_fingerprint = index_fingerprint
        row.extra_metadata = (
            dict(extra_metadata) if extra_metadata is not None else None
        )
        self._session.flush()
        return row

    def _chunk_belongs_to_project(
        self,
        *,
        project_id: UUID,
        chunk_id: UUID,
    ) -> bool:
        statement = (
            select(Chunk.id)
            .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(Chunk.id == chunk_id, Document.project_id == project_id)
        )
        return self._session.scalar(statement) is not None
