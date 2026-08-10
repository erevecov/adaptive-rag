"""Rutas HTTP de authoring publico de workspaces y sources."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from adaptive_rag import authoring
from adaptive_rag.api.dependencies import (
    get_current_user,
    get_session,
    get_workspace_access,
    get_workspace_admin_access,
    get_workspace_contributor_access,
    require_superadmin,
)
from adaptive_rag.api.schemas.authoring import (
    SourceCreateRequestBody,
    SourceListResponse,
    SourceResponse,
    SourceUpdateRequestBody,
    WorkspaceCreateRequestBody,
    WorkspaceListResponse,
    WorkspaceResponse,
    WorkspaceUpdateRequestBody,
)
from adaptive_rag.auth import CurrentPrincipal, get_workspace_role
from adaptive_rag.db.models import Workspace
from adaptive_rag.db.repositories import SourceFilters

router = APIRouter(tags=["authoring"])


@router.post("/workspaces", response_model=WorkspaceResponse)
def create_workspace(
    body: WorkspaceCreateRequestBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> WorkspaceResponse:
    require_superadmin(current)
    try:
        workspace = authoring.create_workspace(
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
    return WorkspaceResponse.from_workspace(
        workspace,
        access_role="superadmin",
        can_access=True,
    )


@router.get("/workspaces", response_model=WorkspaceListResponse)
def list_workspaces(
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> WorkspaceListResponse:
    # Superadmin/bootstrap see all workspaces. Non-superadmin only membership
    # rows at query level (no existence disclosure of foreign workspaces).
    if current.is_superadmin:
        workspaces = authoring.list_workspaces(session)
    elif current.user_id is None:
        workspaces = []
    else:
        workspaces = authoring.list_workspaces(session, member_user_id=current.user_id)
    return WorkspaceListResponse(
        items=[
            _workspace_response_for_current_user(
                session=session,
                current=current,
                workspace=workspace,
            )
            for workspace in workspaces
        ]
    )


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id: UUID,
    access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
) -> WorkspaceResponse:
    workspace, role = access
    return WorkspaceResponse.from_workspace(
        workspace, access_role=role, can_access=True
    )


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: UUID,
    body: WorkspaceUpdateRequestBody,
    session: Annotated[Session, Depends(get_session)],
    access: Annotated[tuple[Workspace, str], Depends(get_workspace_admin_access)],
) -> WorkspaceResponse:
    _workspace, role = access
    try:
        workspace = authoring.update_workspace(
            session,
            workspace_id,
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
    return WorkspaceResponse.from_workspace(
        workspace, access_role=role, can_access=True
    )


@router.delete("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
def delete_workspace(
    workspace_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> WorkspaceResponse:
    require_superadmin(current)
    try:
        workspace = authoring.soft_delete_workspace(session, workspace_id)
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return WorkspaceResponse.from_workspace(
        workspace,
        access_role="superadmin",
        can_access=True,
    )


@router.post("/workspaces/{workspace_id}/sources", response_model=SourceResponse)
def create_source(
    workspace_id: UUID,
    body: SourceCreateRequestBody,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[
        tuple[Workspace, str], Depends(get_workspace_contributor_access)
    ],
) -> SourceResponse:
    try:
        source = authoring.create_source(
            session,
            workspace_id=workspace_id,
            source_type=body.source_type,
            external_id=body.external_id,
            tags=body.tags,
            extra_metadata=body.extra_metadata,
        )
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return SourceResponse.from_source(source)


@router.get("/workspaces/{workspace_id}/sources", response_model=SourceListResponse)
def list_sources(
    workspace_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
    source_type: Annotated[str | None, Query()] = None,
    external_id: Annotated[str | None, Query()] = None,
    tag: Annotated[str | None, Query()] = None,
    created_at_from: Annotated[datetime | None, Query()] = None,
    created_at_to: Annotated[datetime | None, Query()] = None,
) -> SourceListResponse:
    try:
        sources = authoring.list_sources(
            session,
            workspace_id=workspace_id,
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


@router.get(
    "/workspaces/{workspace_id}/sources/{source_id}", response_model=SourceResponse
)
def get_source(
    workspace_id: UUID,
    source_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
) -> SourceResponse:
    try:
        source = authoring.get_source(
            session,
            workspace_id=workspace_id,
            source_id=source_id,
        )
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    return SourceResponse.from_source(source)


@router.patch(
    "/workspaces/{workspace_id}/sources/{source_id}",
    response_model=SourceResponse,
)
def update_source(
    workspace_id: UUID,
    source_id: UUID,
    body: SourceUpdateRequestBody,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[
        tuple[Workspace, str], Depends(get_workspace_contributor_access)
    ],
) -> SourceResponse:
    try:
        source = authoring.update_source(
            session,
            workspace_id=workspace_id,
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
    "/workspaces/{workspace_id}/sources/{source_id}",
    response_model=SourceResponse,
)
def delete_source(
    workspace_id: UUID,
    source_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_admin_access)],
) -> SourceResponse:
    try:
        source = authoring.soft_delete_source(
            session,
            workspace_id=workspace_id,
            source_id=source_id,
        )
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return SourceResponse.from_source(source)


def _http_error(error: authoring.AuthoringError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.detail)


def _workspace_response_for_current_user(
    *,
    session: Session,
    current: CurrentPrincipal,
    workspace: Workspace,
) -> WorkspaceResponse:
    role = get_workspace_role(session, principal=current, workspace_id=workspace.id)
    return WorkspaceResponse.from_workspace(
        workspace,
        access_role=role,
        can_access=role is not None,
    )


@router.get("/workspaces/{workspace_id}/knowledge/dedup-report")
def knowledge_dedup_report(
    workspace_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
) -> dict[str, object]:
    from adaptive_rag.knowledge_lifecycle import (
        build_dedup_report,
        dedup_report_payload,
    )

    try:
        report = build_dedup_report(session, workspace_id=workspace_id)
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    return dedup_report_payload(report)


@router.get("/workspaces/{workspace_id}/sources/{source_id}/sync-status")
def source_sync_status(
    workspace_id: UUID,
    source_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
) -> dict[str, object]:
    from adaptive_rag.knowledge_lifecycle import (
        get_source_sync_status,
        source_sync_status_payload,
    )

    try:
        status = get_source_sync_status(
            session, workspace_id=workspace_id, source_id=source_id
        )
    except authoring.AuthoringError as exc:
        raise _http_error(exc) from exc
    return source_sync_status_payload(status)


@router.post("/workspaces/{workspace_id}/sources/{source_id}/resync", status_code=201)
def source_resync(
    workspace_id: UUID,
    source_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[
        tuple[Workspace, str], Depends(get_workspace_contributor_access)
    ],
) -> dict[str, object]:
    from adaptive_rag.ingestion_ops import job_payload
    from adaptive_rag.knowledge_lifecycle import resync_source

    try:
        result = resync_source(session, workspace_id=workspace_id, source_id=source_id)
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
