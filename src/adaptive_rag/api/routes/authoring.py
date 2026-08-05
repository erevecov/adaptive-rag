"""Rutas HTTP de authoring publico de projects y sources."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from adaptive_rag import authoring
from adaptive_rag.api.dependencies import (
    get_current_user,
    get_project_access,
    get_project_admin_access,
    get_project_contributor_access,
    get_session,
    require_superadmin,
)
from adaptive_rag.api.schemas.authoring import (
    ProjectCreateRequestBody,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequestBody,
    SourceCreateRequestBody,
    SourceListResponse,
    SourceResponse,
    SourceUpdateRequestBody,
)
from adaptive_rag.auth import CurrentPrincipal, get_project_role
from adaptive_rag.db.models import Project
from adaptive_rag.db.repositories import SourceFilters

router = APIRouter(tags=["authoring"])


@router.post("/projects", response_model=ProjectResponse)
def create_project(
    body: ProjectCreateRequestBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> ProjectResponse:
    require_superadmin(current)
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
    return ProjectResponse.from_project(
        project,
        access_role="superadmin",
        can_access=True,
    )


@router.get("/projects", response_model=ProjectListResponse)
def list_projects(
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> ProjectListResponse:
    # Superadmin/bootstrap see all projects. Non-superadmin only membership
    # rows at query level (no existence disclosure of foreign projects).
    if current.is_superadmin:
        projects = authoring.list_projects(session)
    elif current.user_id is None:
        projects = []
    else:
        projects = authoring.list_projects(session, member_user_id=current.user_id)
    return ProjectListResponse(
        items=[
            _project_response_for_current_user(
                session=session,
                current=current,
                project=project,
            )
            for project in projects
        ]
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    access: Annotated[tuple[Project, str], Depends(get_project_access)],
) -> ProjectResponse:
    project, role = access
    return ProjectResponse.from_project(project, access_role=role, can_access=True)


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    body: ProjectUpdateRequestBody,
    session: Annotated[Session, Depends(get_session)],
    access: Annotated[tuple[Project, str], Depends(get_project_admin_access)],
) -> ProjectResponse:
    _project, role = access
    try:
        project = authoring.update_project(
            session,
            project_id,
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
    return ProjectResponse.from_project(project, access_role=role, can_access=True)


@router.delete("/projects/{project_id}", response_model=ProjectResponse)
def delete_project(
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> ProjectResponse:
    require_superadmin(current)
    try:
        project = authoring.soft_delete_project(session, project_id)
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return ProjectResponse.from_project(
        project,
        access_role="superadmin",
        can_access=True,
    )


@router.post("/projects/{project_id}/sources", response_model=SourceResponse)
def create_source(
    project_id: UUID,
    body: SourceCreateRequestBody,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Project, str], Depends(get_project_contributor_access)],
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
    _access: Annotated[tuple[Project, str], Depends(get_project_access)],
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
    _access: Annotated[tuple[Project, str], Depends(get_project_access)],
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


@router.patch(
    "/projects/{project_id}/sources/{source_id}",
    response_model=SourceResponse,
)
def update_source(
    project_id: UUID,
    source_id: UUID,
    body: SourceUpdateRequestBody,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Project, str], Depends(get_project_contributor_access)],
) -> SourceResponse:
    try:
        source = authoring.update_source(
            session,
            project_id=project_id,
            source_id=source_id,
            tags=body.tags,
            extra_metadata=body.extra_metadata,
            external_id=body.external_id,
        )
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return SourceResponse.from_source(source)


@router.delete(
    "/projects/{project_id}/sources/{source_id}",
    response_model=SourceResponse,
)
def delete_source(
    project_id: UUID,
    source_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Project, str], Depends(get_project_admin_access)],
) -> SourceResponse:
    try:
        source = authoring.soft_delete_source(
            session,
            project_id=project_id,
            source_id=source_id,
        )
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return SourceResponse.from_source(source)


def _http_error(error: authoring.AuthoringError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.detail)


def _project_response_for_current_user(
    *,
    session: Session,
    current: CurrentPrincipal,
    project: Project,
) -> ProjectResponse:
    role = get_project_role(session, principal=current, project_id=project.id)
    return ProjectResponse.from_project(
        project,
        access_role=role,
        can_access=role is not None,
    )


@router.get("/projects/{project_id}/knowledge/dedup-report")
def knowledge_dedup_report(
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Project, str], Depends(get_project_access)],
) -> dict[str, object]:
    from adaptive_rag.knowledge_lifecycle import (
        build_dedup_report,
        dedup_report_payload,
    )

    try:
        report = build_dedup_report(session, project_id=project_id)
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    return dedup_report_payload(report)


@router.get("/projects/{project_id}/sources/{source_id}/sync-status")
def source_sync_status(
    project_id: UUID,
    source_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Project, str], Depends(get_project_access)],
) -> dict[str, object]:
    from adaptive_rag.knowledge_lifecycle import (
        get_source_sync_status,
        source_sync_status_payload,
    )

    try:
        status = get_source_sync_status(
            session, project_id=project_id, source_id=source_id
        )
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    return source_sync_status_payload(status)


@router.post("/projects/{project_id}/sources/{source_id}/resync", status_code=201)
def source_resync(
    project_id: UUID,
    source_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Project, str], Depends(get_project_contributor_access)],
) -> dict[str, object]:
    from adaptive_rag.ingestion_ops import job_payload
    from adaptive_rag.knowledge_lifecycle import resync_source

    try:
        result = resync_source(session, project_id=project_id, source_id=source_id)
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    except Exception as exc:
        # IngestionOpsError may be raised
        from adaptive_rag.ingestion_ops import IngestionOpsError

        if isinstance(exc, IngestionOpsError):
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        raise
    session.commit()
    return {"source_id": str(result.source_id), "job": job_payload(result.job)}
