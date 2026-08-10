"""Repository de chunks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Chunk, Document, DocumentVersion


class ChunkRepository:
    """Acceso a chunks con validacion de pertenencia por proyecto."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        workspace_id: UUID,
        document_version_id: UUID,
        ordinal: int,
        char_start: int,
        char_end: int,
        token_count: int | None = None,
        section_metadata: Mapping[str, Any] | None = None,
        chunker_metadata: Mapping[str, Any] | None = None,
        contextual_summary: str | None = None,
        embedding: Sequence[float] | None = None,
    ) -> Chunk:
        if not self._version_belongs_to_workspace(
            workspace_id=workspace_id, document_version_id=document_version_id
        ):
            raise ValueError("document version does not belong to workspace")

        chunk = Chunk(
            document_version_id=document_version_id,
            ordinal=ordinal,
            char_start=char_start,
            char_end=char_end,
            token_count=token_count,
            section_metadata=(
                dict(section_metadata) if section_metadata is not None else None
            ),
            chunker_metadata=dict(chunker_metadata)
            if chunker_metadata is not None
            else None,
            contextual_summary=contextual_summary,
            embedding=list(embedding) if embedding is not None else None,
        )
        self._session.add(chunk)
        self._session.flush()
        return chunk

    def list_by_document_version(
        self,
        *,
        workspace_id: UUID,
        document_version_id: UUID,
    ) -> list[Chunk]:
        statement = (
            select(Chunk)
            .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(
                Chunk.document_version_id == document_version_id,
                Document.workspace_id == workspace_id,
            )
            .order_by(Chunk.ordinal)
        )
        return list(self._session.scalars(statement))

    def update_dense_embedding(
        self,
        *,
        workspace_id: UUID,
        chunk_id: UUID,
        embedding: Sequence[float],
        embedding_metadata: Mapping[str, Any],
    ) -> Chunk:
        chunk = self._get_chunk_for_workspace(
            workspace_id=workspace_id, chunk_id=chunk_id
        )
        if chunk is None:
            raise ValueError("chunk does not belong to workspace")

        chunk.embedding = list(embedding)
        chunk.embedding_metadata = dict(embedding_metadata)
        self._session.flush()
        return chunk

    def update_contextual_summary(
        self,
        *,
        workspace_id: UUID,
        chunk_id: UUID,
        contextual_summary: str,
    ) -> Chunk:
        chunk = self._get_chunk_for_workspace(
            workspace_id=workspace_id, chunk_id=chunk_id
        )
        if chunk is None:
            raise ValueError("chunk does not belong to workspace")

        chunk.contextual_summary = contextual_summary
        self._session.flush()
        return chunk

    def _get_chunk_for_workspace(
        self,
        *,
        workspace_id: UUID,
        chunk_id: UUID,
    ) -> Chunk | None:
        statement = (
            select(Chunk)
            .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(Chunk.id == chunk_id, Document.workspace_id == workspace_id)
        )
        return self._session.scalars(statement).one_or_none()

    def _version_belongs_to_workspace(
        self, *, workspace_id: UUID, document_version_id: UUID
    ) -> bool:
        statement = (
            select(DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(
                DocumentVersion.id == document_version_id,
                Document.workspace_id == workspace_id,
            )
        )
        return self._session.scalar(statement) is not None
