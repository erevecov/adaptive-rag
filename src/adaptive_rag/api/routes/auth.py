"""Routes for local users and project memberships."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from adaptive_rag.api.dependencies import (
    get_current_user,
    get_project_admin_access,
    get_session,
    require_superadmin,
)
from adaptive_rag.api.schemas.auth import (
    CurrentUserPreferencesRequestBody,
    CurrentUserResponse,
    ProjectMembershipListResponse,
    ProjectMembershipResponse,
    ProjectMembershipUpsertRequestBody,
    UserCreateRequestBody,
    UserListResponse,
    UserResponse,
)
from adaptive_rag.auth import CurrentPrincipal, get_project_role, hash_access_token
from adaptive_rag.db.models import Project
from adaptive_rag.db.repositories import ProjectMembershipRepository, UserRepository

router = APIRouter(tags=["auth"])


@router.get("/auth/me", response_model=CurrentUserResponse)
def get_me(
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> CurrentUserResponse:
    return CurrentUserResponse.from_principal(current)


@router.patch("/auth/me/preferences", response_model=CurrentUserResponse)
def update_me_preferences(
    body: CurrentUserPreferencesRequestBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> CurrentUserResponse:
    if current.user_id is None:
        raise HTTPException(status_code=401, detail="authenticated user required")

    if body.last_project_id is not None:
        if session.get(Project, body.last_project_id) is None:
            raise HTTPException(status_code=404, detail="project not found")
        if (
            get_project_role(
                session,
                principal=current,
                project_id=body.last_project_id,
            )
            is None
        ):
            raise HTTPException(status_code=403, detail="project access required")

    user = UserRepository(session).update_last_project_id(
        current.user_id,
        last_project_id=body.last_project_id,
    )
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    session.commit()
    return CurrentUserResponse.from_principal(CurrentPrincipal(user=user))


@router.get("/admin/users", response_model=UserListResponse)
def list_users(
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> UserListResponse:
    require_superadmin(current)
    return UserListResponse.from_users(UserRepository(session).list_users())


@router.post("/admin/users", response_model=UserResponse)
def create_user(
    body: UserCreateRequestBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> UserResponse:
    if current.is_bootstrap and body.system_role != "superadmin":
        raise HTTPException(
            status_code=403,
            detail="bootstrap can only create the first superadmin",
        )
    if not current.is_bootstrap:
        require_superadmin(current)

    try:
        repo = UserRepository(session)
        user = repo.create_user(
            login=body.login,
            display_name=body.display_name,
            system_role=body.system_role,
            is_active=body.is_active,
        )
        if body.access_token is not None:
            repo.upsert_access_token(
                user_id=user.id,
                token_hash=hash_access_token(body.access_token),
                label="created via admin api",
            )
    except ValueError as exc:
        detail = str(exc)
        status_code = 409 if detail == "user_login_already_exists" else 422
        raise HTTPException(status_code=status_code, detail=detail) from exc
    session.commit()
    return UserResponse.from_user(user)


@router.get(
    "/projects/{project_id}/memberships",
    response_model=ProjectMembershipListResponse,
)
def list_project_memberships(
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[object, str], Depends(get_project_admin_access)],
) -> ProjectMembershipListResponse:
    memberships = ProjectMembershipRepository(session).list_project_members(
        project_id=project_id
    )
    return ProjectMembershipListResponse.from_memberships(memberships)


@router.put(
    "/projects/{project_id}/memberships/{user_id}",
    response_model=ProjectMembershipResponse,
)
def upsert_project_membership(
    project_id: UUID,
    user_id: UUID,
    body: ProjectMembershipUpsertRequestBody,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[object, str], Depends(get_project_admin_access)],
) -> ProjectMembershipResponse:
    if UserRepository(session).get_user(user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    try:
        membership = ProjectMembershipRepository(session).upsert_membership(
            project_id=project_id,
            user_id=user_id,
            role=body.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    session.commit()
    return ProjectMembershipResponse.from_membership(membership)
