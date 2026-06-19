"""Repository de documents y document versions."""

from __future__ import annotations

import builtins
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Document, DocumentVersion, Source
from adaptive_rag.db.repositories.filters import DocumentFilters


class DocumentRepository:
    """Acceso a documents y versions con pertenencia de proyecto explicita."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_document(
        self,
        *,
        project_id: UUID,
        source_id: UUID,
        stable_id: str,
    ) -> Document:
        if not self._source_belongs_to_project(
            project_id=project_id, source_id=source_id
        ):
            raise ValueError("source does not belong to project")

        document = Document(
            project_id=project_id,
            source_id=source_id,
            stable_id=stable_id,
        )
        self._session.add(document)
        self._session.flush()
        return document

    def list(
        self,
        *,
        project_id: UUID,
        filters: DocumentFilters | None = None,
    ) -> builtins.list[Document]:
        active_filters = filters or DocumentFilters()
        statement = select(Document).where(Document.project_id == project_id)

        if active_filters.source_id is not None:
            statement = statement.where(Document.source_id == active_filters.source_id)
        if active_filters.stable_id is not None:
            statement = statement.where(Document.stable_id == active_filters.stable_id)
        if active_filters.created_at_from is not None:
            statement = statement.where(
                Document.created_at >= active_filters.created_at_from
            )
        if active_filters.created_at_to is not None:
            statement = statement.where(
                Document.created_at <= active_filters.created_at_to
            )

        statement = statement.order_by(Document.created_at, Document.stable_id)
        return builtins.list(self._session.scalars(statement))

    def create_version(
        self,
        *,
        project_id: UUID,
        document_id: UUID,
        version_number: int,
        normalized_text: str,
        content_hash: str,
        index_fingerprint: str,
        parser_metadata: Mapping[str, Any] | None = None,
        extraction_metadata: Mapping[str, Any] | None = None,
    ) -> DocumentVersion:
        if not self._document_belongs_to_project(
            project_id=project_id, document_id=document_id
        ):
            raise ValueError("document does not belong to project")

        version = DocumentVersion(
            document_id=document_id,
            version_number=version_number,
            normalized_text=normalized_text,
            content_hash=content_hash,
            index_fingerprint=index_fingerprint,
            parser_metadata=(
                dict(parser_metadata) if parser_metadata is not None else None
            ),
            extraction_metadata=(
                dict(extraction_metadata) if extraction_metadata is not None else None
            ),
        )
        self._session.add(version)
        self._session.flush()
        return version

    def list_versions(
        self,
        *,
        project_id: UUID,
        document_id: UUID,
    ) -> builtins.list[DocumentVersion]:
        statement = (
            select(DocumentVersion)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(Document.id == document_id, Document.project_id == project_id)
            .order_by(DocumentVersion.version_number)
        )
        return builtins.list(self._session.scalars(statement))

    def get_version(
        self,
        *,
        project_id: UUID,
        document_version_id: UUID,
    ) -> DocumentVersion | None:
        statement = (
            select(DocumentVersion)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(
                DocumentVersion.id == document_version_id,
                Document.project_id == project_id,
            )
        )
        return self._session.scalars(statement).one_or_none()

    def _source_belongs_to_project(self, *, project_id: UUID, source_id: UUID) -> bool:
        statement = select(Source.id).where(
            Source.id == source_id,
            Source.project_id == project_id,
        )
        return self._session.scalar(statement) is not None

    def _document_belongs_to_project(
        self, *, project_id: UUID, document_id: UUID
    ) -> bool:
        statement = select(Document.id).where(
            Document.id == document_id,
            Document.project_id == project_id,
        )
        return self._session.scalar(statement) is not None
