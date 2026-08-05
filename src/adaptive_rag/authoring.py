"""Operaciones publicas de authoring para projects y sources."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, NoReturn
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Project, Source
from adaptive_rag.db.repositories import (
    ProjectRepository,
    SourceFilters,
    SourceRepository,
)
from adaptive_rag.ingestion.parsers import (
    BINARY_SOURCE_TYPES,
    MAX_BINARY_SOURCE_BYTES,
    decode_content_base64,
)

SUPPORTED_SOURCE_TYPES = ("markdown", "text", "txt", "url", "pdf", "docx")
TEXT_SOURCE_TYPES = frozenset({"markdown", "text", "txt"})
# Align text body cap with binary payload limit (5 MiB) so JSON content stays
# in the same order of magnitude as content_base64 uploads.
MAX_TEXT_SOURCE_CONTENT_CHARS = MAX_BINARY_SOURCE_BYTES


class AuthoringError(Exception):
    """Error esperado de authoring con mensaje estable para API y CLI."""

    def __init__(self, detail: str, *, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def create_project(
    session: Session,
    *,
    name: str,
    embedding_mode: str = "dense_sparse",
    retrieval_contextualization_enabled: bool = True,
    budget_config_json: Mapping[str, Any] | None = None,
) -> Project:
    if embedding_mode not in {"dense", "dense_sparse"}:
        raise AuthoringError(
            "project embedding_mode must be dense or dense_sparse",
            status_code=422,
        )
    return ProjectRepository(session).create(
        name=name,
        embedding_mode=embedding_mode,
        retrieval_contextualization_enabled=retrieval_contextualization_enabled,
        budget_config_json=budget_config_json,
    )


def list_projects(session: Session) -> list[Project]:
    return ProjectRepository(session).list()


def get_project(session: Session, project_id: UUID) -> Project:
    project = ProjectRepository(session).get(project_id)
    if project is None:
        raise AuthoringError("project not found", status_code=404)
    return project


def create_source(
    session: Session,
    *,
    project_id: UUID,
    source_type: str,
    external_id: str,
    tags: Sequence[str] | None = None,
    extra_metadata: Mapping[str, Any] | None = None,
) -> Source:
    get_project(session, project_id)
    validate_source_create(
        source_type=source_type,
        extra_metadata=extra_metadata,
    )
    source_repository = SourceRepository(session)
    existing = source_repository.get_by_identity(
        project_id=project_id,
        source_type=source_type,
        external_id=external_id,
    )
    if existing is not None:
        raise AuthoringError("source already exists", status_code=409)
    deleted = source_repository.get_by_identity(
        project_id=project_id,
        source_type=source_type,
        external_id=external_id,
        include_deleted=True,
    )
    if deleted is not None:
        # Unique identity still counts soft-deleted rows; revive instead of 409 forever.
        restored = source_repository.restore(
            project_id=project_id,
            source_id=deleted.id,
            tags=tags,
            extra_metadata=extra_metadata,
        )
        if restored is None:
            raise AuthoringError("source not found", status_code=404)
        return restored
    try:
        return source_repository.create(
            project_id=project_id,
            source_type=source_type,
            external_id=external_id,
            tags=tags,
            extra_metadata=extra_metadata,
        )
    except IntegrityError as exc:
        session.rollback()
        raise AuthoringError("source already exists", status_code=409) from exc


def list_sources(
    session: Session,
    *,
    project_id: UUID,
    filters: SourceFilters | None = None,
) -> list[Source]:
    get_project(session, project_id)
    return SourceRepository(session).list(project_id=project_id, filters=filters)


def get_source(session: Session, *, project_id: UUID, source_id: UUID) -> Source:
    get_project(session, project_id)
    source = SourceRepository(session).get(project_id=project_id, source_id=source_id)
    if source is None:
        raise AuthoringError("source not found", status_code=404)
    return source


def update_project(
    session: Session,
    project_id: UUID,
    *,
    name: str | None = None,
    embedding_mode: str | None = None,
    retrieval_contextualization_enabled: bool | None = None,
    budget_config_json: Mapping[str, Any] | None = None,
) -> Project:
    get_project(session, project_id)
    if embedding_mode is not None and embedding_mode not in {"dense", "dense_sparse"}:
        raise AuthoringError(
            "project embedding_mode must be dense or dense_sparse",
            status_code=422,
        )
    if name is not None and not name.strip():
        raise AuthoringError("project name must not be empty", status_code=422)
    project = ProjectRepository(session).update(
        project_id,
        name=name.strip() if name is not None else None,
        embedding_mode=embedding_mode,
        retrieval_contextualization_enabled=retrieval_contextualization_enabled,
        budget_config_json=budget_config_json,
    )
    if project is None:
        raise AuthoringError("project not found", status_code=404)
    return project


def soft_delete_project(session: Session, project_id: UUID) -> Project:
    project = ProjectRepository(session).soft_delete(project_id)
    if project is None:
        raise AuthoringError("project not found", status_code=404)
    return project


def update_source(
    session: Session,
    *,
    project_id: UUID,
    source_id: UUID,
    tags: Sequence[str] | None = None,
    extra_metadata: Mapping[str, Any] | None = None,
    external_id: str | None = None,
) -> Source:
    get_source(session, project_id=project_id, source_id=source_id)
    if external_id is not None and not external_id.strip():
        raise AuthoringError("external_id must not be empty", status_code=422)
    if extra_metadata is not None:
        source = SourceRepository(session).get(
            project_id=project_id, source_id=source_id
        )
        if source is None:
            raise AuthoringError("source not found", status_code=404)
        validate_source_create(
            source_type=source.source_type,
            extra_metadata=extra_metadata,
        )
    try:
        updated = SourceRepository(session).update(
            project_id=project_id,
            source_id=source_id,
            tags=tags,
            extra_metadata=extra_metadata,
            external_id=external_id.strip() if external_id is not None else None,
        )
    except IntegrityError as exc:
        session.rollback()
        raise AuthoringError("source already exists", status_code=409) from exc
    if updated is None:
        raise AuthoringError("source not found", status_code=404)
    return updated


def soft_delete_source(
    session: Session,
    *,
    project_id: UUID,
    source_id: UUID,
) -> Source:
    source = SourceRepository(session).soft_delete(
        project_id=project_id,
        source_id=source_id,
    )
    if source is None:
        raise AuthoringError("source not found", status_code=404)
    _cascade_delete_source_index(session, project_id=project_id, source_id=source_id)
    return source


def _cascade_delete_source_index(
    session: Session,
    *,
    project_id: UUID,
    source_id: UUID,
) -> None:
    """Remove searchable index rows for a soft-deleted source."""

    from sqlalchemy import delete, select

    from adaptive_rag.db.models import (
        Chunk,
        ChunkSparseEmbedding,
        Document,
        DocumentVersion,
    )

    document_ids = list(
        session.scalars(
            select(Document.id).where(
                Document.project_id == project_id,
                Document.source_id == source_id,
            )
        )
    )
    if not document_ids:
        return
    version_ids = list(
        session.scalars(
            select(DocumentVersion.id).where(
                DocumentVersion.document_id.in_(document_ids)
            )
        )
    )
    if version_ids:
        chunk_ids = list(
            session.scalars(
                select(Chunk.id).where(Chunk.document_version_id.in_(version_ids))
            )
        )
        if chunk_ids:
            session.execute(
                delete(ChunkSparseEmbedding).where(
                    ChunkSparseEmbedding.chunk_id.in_(chunk_ids)
                )
            )
            session.execute(delete(Chunk).where(Chunk.id.in_(chunk_ids)))
        session.execute(
            delete(DocumentVersion).where(DocumentVersion.id.in_(version_ids))
        )
    session.execute(
        delete(Document).where(
            Document.project_id == project_id,
            Document.id.in_(document_ids),
        )
    )
    session.flush()


def validate_source_create(
    *,
    source_type: str,
    extra_metadata: Mapping[str, Any] | None,
) -> None:
    if source_type not in SUPPORTED_SOURCE_TYPES:
        raise AuthoringError(
            "source_type must be one of markdown, text, txt, url, pdf, docx",
            status_code=422,
        )
    if source_type in TEXT_SOURCE_TYPES:
        if extra_metadata is None:
            _raise_missing_text_content(source_type)
        content = extra_metadata.get("content")
        if not isinstance(content, str) or content.strip() == "":
            _raise_missing_text_content(source_type)
        if len(content) > MAX_TEXT_SOURCE_CONTENT_CHARS:
            raise AuthoringError(
                f"{source_type} source content exceeds max size of "
                f"{MAX_TEXT_SOURCE_CONTENT_CHARS} characters",
                status_code=422,
            )
        return
    if source_type in BINARY_SOURCE_TYPES:
        _validate_binary_source_metadata(
            source_type=source_type,
            extra_metadata=extra_metadata,
        )


def project_payload(project: Project) -> dict[str, Any]:
    return {
        "id": str(project.id),
        "name": project.name,
        "embedding_mode": project.embedding_mode,
        "retrieval_contextualization_enabled": (
            project.retrieval_contextualization_enabled
        ),
        "budget_config_json": project.budget_config_json,
        "created_at": _datetime_payload(project.created_at),
        "updated_at": _datetime_payload(project.updated_at),
    }


def source_payload(source: Source) -> dict[str, Any]:
    return {
        "id": str(source.id),
        "project_id": str(source.project_id),
        "source_type": source.source_type,
        "external_id": source.external_id,
        "tags": source.tags,
        "extra_metadata": source.extra_metadata,
        "created_at": _datetime_payload(source.created_at),
        "updated_at": _datetime_payload(source.updated_at),
    }


def _raise_missing_text_content(source_type: str) -> NoReturn:
    raise AuthoringError(
        f"{source_type} source requires extra_metadata.content",
        status_code=422,
    )


def _validate_binary_source_metadata(
    *,
    source_type: str,
    extra_metadata: Mapping[str, Any] | None,
) -> None:
    if extra_metadata is None:
        raise AuthoringError(
            f"{source_type} source requires extra_metadata.content_base64",
            status_code=422,
        )
    try:
        decode_content_base64(
            extra_metadata.get("content_base64"),
            max_bytes=MAX_BINARY_SOURCE_BYTES,
            source_type=source_type,
        )
    except ValueError as exc:
        raise AuthoringError(str(exc), status_code=422) from exc


def _datetime_payload(value: datetime) -> str:
    return value.isoformat()
