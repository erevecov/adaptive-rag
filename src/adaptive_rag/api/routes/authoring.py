"""Rutas HTTP de authoring publico de projects y sources."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from adaptive_rag.api.dependencies import get_session
from adaptive_rag.api.schemas.authoring import (
    ProjectCreateRequestBody,
    ProjectListResponse,
    ProjectResponse,
    SourceCreateRequestBody,
    SourceListResponse,
    SourceResponse,
)
from adaptive_rag.db.repositories import (
    ProjectRepository,
    SourceFilters,
    SourceRepository,
)

router = APIRouter(tags=["authoring"])

SUPPORTED_SOURCE_TYPES = ("markdown", "text", "txt", "url")
TEXT_SOURCE_TYPES = frozenset({"markdown", "text", "txt"})


@router.post("/projects", response_model=ProjectResponse)
def create_project(
    body: ProjectCreateRequestBody,
    session: Annotated[Session, Depends(get_session)],
) -> ProjectResponse:
    if body.embedding_mode != "dense":
        raise HTTPException(
            status_code=422,
            detail="project embedding_mode must be dense",
        )
    project = ProjectRepository(session).create(
        name=body.name,
        embedding_mode=body.embedding_mode,
        retrieval_contextualization_enabled=(
            body.retrieval_contextualization_enabled
        ),
        budget_config_json=body.budget_config_json,
    )
    session.commit()
    return ProjectResponse.from_project(project)


@router.get("/projects", response_model=ProjectListResponse)
def list_projects(
    session: Annotated[Session, Depends(get_session)],
) -> ProjectListResponse:
    projects = ProjectRepository(session).list()
    return ProjectListResponse.from_projects(projects)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> ProjectResponse:
    project = ProjectRepository(session).get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return ProjectResponse.from_project(project)


@router.post("/projects/{project_id}/sources", response_model=SourceResponse)
def create_source(
    project_id: UUID,
    body: SourceCreateRequestBody,
    session: Annotated[Session, Depends(get_session)],
) -> SourceResponse:
    _ensure_project_exists(project_id=project_id, session=session)
    _validate_source_create_body(body)
    source_repository = SourceRepository(session)
    existing = source_repository.get_by_identity(
        project_id=project_id,
        source_type=body.source_type,
        external_id=body.external_id,
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="source already exists")
    try:
        source = source_repository.create(
            project_id=project_id,
            source_type=body.source_type,
            external_id=body.external_id,
            tags=body.tags,
            extra_metadata=body.extra_metadata,
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="source already exists") from exc
    return SourceResponse.from_source(source)


@router.get("/projects/{project_id}/sources", response_model=SourceListResponse)
def list_sources(
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    source_type: Annotated[str | None, Query()] = None,
    external_id: Annotated[str | None, Query()] = None,
    tag: Annotated[str | None, Query()] = None,
    created_at_from: Annotated[datetime | None, Query()] = None,
    created_at_to: Annotated[datetime | None, Query()] = None,
) -> SourceListResponse:
    _ensure_project_exists(project_id=project_id, session=session)
    sources = SourceRepository(session).list(
        project_id=project_id,
        filters=SourceFilters(
            source_type=source_type,
            external_id=external_id,
            tag=tag,
            created_at_from=created_at_from,
            created_at_to=created_at_to,
        ),
    )
    return SourceListResponse.from_sources(sources)


@router.get("/projects/{project_id}/sources/{source_id}", response_model=SourceResponse)
def get_source(
    project_id: UUID,
    source_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> SourceResponse:
    _ensure_project_exists(project_id=project_id, session=session)
    source = SourceRepository(session).get(project_id=project_id, source_id=source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="source not found")
    return SourceResponse.from_source(source)


def _ensure_project_exists(*, project_id: UUID, session: Session) -> None:
    if ProjectRepository(session).get(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")


def _validate_source_create_body(body: SourceCreateRequestBody) -> None:
    if body.source_type not in SUPPORTED_SOURCE_TYPES:
        raise HTTPException(
            status_code=422,
            detail="source_type must be one of markdown, text, txt, url",
        )
    if body.source_type not in TEXT_SOURCE_TYPES:
        return
    extra_metadata = body.extra_metadata
    if extra_metadata is None:
        _raise_missing_text_content(body.source_type)
    content = extra_metadata.get("content")
    if not isinstance(content, str) or content.strip() == "":
        _raise_missing_text_content(body.source_type)


def _raise_missing_text_content(source_type: str) -> NoReturn:
    raise HTTPException(
        status_code=422,
        detail=f"{source_type} source requires extra_metadata.content",
    )
