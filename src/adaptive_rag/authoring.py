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

SUPPORTED_SOURCE_TYPES = ("markdown", "text", "txt", "url")
TEXT_SOURCE_TYPES = frozenset({"markdown", "text", "txt"})


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
    embedding_mode: str = "dense",
    retrieval_contextualization_enabled: bool = True,
    budget_config_json: Mapping[str, Any] | None = None,
) -> Project:
    if embedding_mode != "dense":
        raise AuthoringError(
            "project embedding_mode must be dense",
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


def validate_source_create(
    *,
    source_type: str,
    extra_metadata: Mapping[str, Any] | None,
) -> None:
    if source_type not in SUPPORTED_SOURCE_TYPES:
        raise AuthoringError(
            "source_type must be one of markdown, text, txt, url",
            status_code=422,
        )
    if source_type not in TEXT_SOURCE_TYPES:
        return
    if extra_metadata is None:
        _raise_missing_text_content(source_type)
    content = extra_metadata.get("content")
    if not isinstance(content, str) or content.strip() == "":
        _raise_missing_text_content(source_type)


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


def _datetime_payload(value: datetime) -> str:
    return value.isoformat()
