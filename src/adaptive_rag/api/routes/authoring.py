"""Rutas HTTP de authoring publico de projects y sources."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from adaptive_rag import authoring
from adaptive_rag.api.dependencies import get_session
from adaptive_rag.api.schemas.authoring import (
    ProjectCreateRequestBody,
    ProjectListResponse,
    ProjectResponse,
    SourceCreateRequestBody,
    SourceListResponse,
    SourceResponse,
)
from adaptive_rag.db.repositories import SourceFilters

router = APIRouter(tags=["authoring"])


@router.post("/projects", response_model=ProjectResponse)
def create_project(
    body: ProjectCreateRequestBody,
    session: Annotated[Session, Depends(get_session)],
) -> ProjectResponse:
    try:
        project = authoring.create_project(
            session,
            name=body.name,
            embedding_mode=body.embedding_mode,
            retrieval_contextualization_enabled=(
                body.retrieval_contextualization_enabled
            ),
            budget_config_json=body.budget_config_json,
        )
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return ProjectResponse.from_project(project)


@router.get("/projects", response_model=ProjectListResponse)
def list_projects(
    session: Annotated[Session, Depends(get_session)],
) -> ProjectListResponse:
    projects = authoring.list_projects(session)
    return ProjectListResponse.from_projects(projects)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> ProjectResponse:
    try:
        project = authoring.get_project(session, project_id)
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    return ProjectResponse.from_project(project)


@router.post("/projects/{project_id}/sources", response_model=SourceResponse)
def create_source(
    project_id: UUID,
    body: SourceCreateRequestBody,
    session: Annotated[Session, Depends(get_session)],
) -> SourceResponse:
    try:
        source = authoring.create_source(
            session,
            project_id=project_id,
            source_type=body.source_type,
            external_id=body.external_id,
            tags=body.tags,
            extra_metadata=body.extra_metadata,
        )
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    session.commit()
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
    try:
        sources = authoring.list_sources(
            session,
            project_id=project_id,
            filters=SourceFilters(
                source_type=source_type,
                external_id=external_id,
                tag=tag,
                created_at_from=created_at_from,
                created_at_to=created_at_to,
            ),
        )
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    return SourceListResponse.from_sources(sources)


@router.get("/projects/{project_id}/sources/{source_id}", response_model=SourceResponse)
def get_source(
    project_id: UUID,
    source_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> SourceResponse:
    try:
        source = authoring.get_source(
            session,
            project_id=project_id,
            source_id=source_id,
        )
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    return SourceResponse.from_source(source)


def _http_error(error: authoring.AuthoringError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.detail)
