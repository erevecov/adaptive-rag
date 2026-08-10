"""Routes for local users and workspace memberships."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from adaptive_rag.api.dependencies import (
    get_current_user,
    get_session,
    get_workspace_admin_access,
    require_superadmin,
)
from adaptive_rag.api.schemas.auth import (
    AccessTokenRevokeRequestBody,
    CurrentUserPreferencesRequestBody,
    CurrentUserResponse,
    UserCreateRequestBody,
    UserListResponse,
    UserResponse,
    WorkspaceMembershipListResponse,
    WorkspaceMembershipResponse,
    WorkspaceMembershipUpsertRequestBody,
)
from adaptive_rag.auth import CurrentPrincipal, get_workspace_role, hash_access_token
from adaptive_rag.db.repositories import (
    UserRepository,
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)

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

    if body.last_workspace_id is not None:
        if WorkspaceRepository(session).get(body.last_workspace_id) is None:
            raise HTTPException(status_code=404, detail="workspace not found")
        if (
            get_workspace_role(
                session,
                principal=current,
                workspace_id=body.last_workspace_id,
            )
            is None
        ):
            raise HTTPException(status_code=403, detail="workspace access required")

    user = UserRepository(session).update_last_workspace_id(
        current.user_id,
        last_workspace_id=body.last_workspace_id,
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
    "/workspaces/{workspace_id}/memberships",
    response_model=WorkspaceMembershipListResponse,
)
def list_workspace_memberships(
    workspace_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[object, str], Depends(get_workspace_admin_access)],
) -> WorkspaceMembershipListResponse:
    memberships = WorkspaceMembershipRepository(session).list_workspace_members(
        workspace_id=workspace_id
    )
    return WorkspaceMembershipListResponse.from_memberships(memberships)


@router.put(
    "/workspaces/{workspace_id}/memberships/{user_id}",
    response_model=WorkspaceMembershipResponse,
)
def upsert_workspace_membership(
    workspace_id: UUID,
    user_id: UUID,
    body: WorkspaceMembershipUpsertRequestBody,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[object, str], Depends(get_workspace_admin_access)],
) -> WorkspaceMembershipResponse:
    if UserRepository(session).get_user(user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    try:
        membership = WorkspaceMembershipRepository(session).upsert_membership(
            workspace_id=workspace_id,
            user_id=user_id,
            role=body.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    session.commit()
    return WorkspaceMembershipResponse.from_membership(membership)


@router.delete(
    "/workspaces/{workspace_id}/memberships/{user_id}",
    status_code=204,
)
def delete_workspace_membership(
    workspace_id: UUID,
    user_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[object, str], Depends(get_workspace_admin_access)],
) -> None:
    removed = WorkspaceMembershipRepository(session).remove_membership(
        workspace_id=workspace_id,
        user_id=user_id,
    )
    if not removed:
        raise HTTPException(status_code=404, detail="membership not found")
    session.commit()


@router.post("/admin/users/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> UserResponse:
    require_superadmin(current)
    user = UserRepository(session).update_user(user_id, is_active=False)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    session.commit()
    return UserResponse.from_user(user)


@router.post("/admin/access-tokens/revoke")
def revoke_access_token(
    body: AccessTokenRevokeRequestBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> dict[str, bool]:
    require_superadmin(current)
    if not body.access_token.strip():
        raise HTTPException(status_code=422, detail="access_token is required")
    revoked = UserRepository(session).revoke_access_token(
        hash_access_token(body.access_token)
    )
    if not revoked:
        raise HTTPException(status_code=404, detail="access token not found")
    session.commit()
    return {"revoked": True}
