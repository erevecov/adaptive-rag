"""Schemas HTTP for local users and workspace memberships."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from adaptive_rag.auth import CurrentPrincipal
from adaptive_rag.db.models import User, WorkspaceMembership


class UserCreateRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    display_name: str
    system_role: Literal["user", "superadmin"] = "user"
    initial_workspace_id: UUID | None = None
    initial_workspace_role: Literal["viewer", "contributor", "admin"] | None = None


class SetupRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    display_name: str
    password: str


class LoginRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str


class ChangePasswordRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str | None = None
    new_password: str


class CsrfTokenResponse(BaseModel):
    csrf_token: str


class AccessTokenRevokeRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    system_role: str
    is_active: bool
    last_workspace_id: UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_user(cls, user: User) -> UserResponse:
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            system_role=user.system_role,
            is_active=user.is_active,
            last_workspace_id=user.last_workspace_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class UserMembershipSummary(BaseModel):
    workspace_id: UUID
    workspace_name: str
    role: Literal["viewer", "contributor", "admin"]


class AdminUserResponse(UserResponse):
    must_change_password: bool
    memberships: list[UserMembershipSummary]


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]


class UserCreateResponse(BaseModel):
    user: AdminUserResponse
    temporary_password: str


class UserUpdateRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = None
    display_name: str | None = None
    system_role: Literal["user", "superadmin"] | None = None


class TemporaryPasswordResponse(BaseModel):
    user: AdminUserResponse
    temporary_password: str


class WorkspaceMemberAddRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    role: Literal["viewer", "contributor", "admin"]


class WorkspaceMemberUpdateRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["viewer", "contributor", "admin"]


class WorkspaceMemberResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    email: str
    display_name: str
    is_active: bool
    role: Literal["viewer", "contributor", "admin"]
    created_at: datetime
    updated_at: datetime


class WorkspaceMemberListResponse(BaseModel):
    items: list[WorkspaceMemberResponse]


class CurrentUserPreferencesRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    last_workspace_id: UUID | None = None


class CurrentUserResponse(BaseModel):
    id: UUID | None
    email: str
    display_name: str
    system_role: str
    must_change_password: bool
    last_workspace_id: UUID | None

    @classmethod
    def from_principal(cls, principal: CurrentPrincipal) -> CurrentUserResponse:
        return cls(
            id=principal.user_id,
            email=principal.email,
            display_name=principal.display_name,
            system_role=principal.system_role,
            must_change_password=principal.must_change_password,
            last_workspace_id=(
                None if principal.user is None else principal.user.last_workspace_id
            ),
        )


class UserListResponse(BaseModel):
    items: list[UserResponse]

    @classmethod
    def from_users(cls, users: list[User]) -> UserListResponse:
        return cls(items=[UserResponse.from_user(user) for user in users])


class WorkspaceMembershipUpsertRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str


class WorkspaceMembershipResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_membership(
        cls,
        membership: WorkspaceMembership,
    ) -> WorkspaceMembershipResponse:
        return cls(
            id=membership.id,
            workspace_id=membership.workspace_id,
            user_id=membership.user_id,
            role=membership.role,
            created_at=membership.created_at,
            updated_at=membership.updated_at,
        )


class WorkspaceMembershipListResponse(BaseModel):
    items: list[WorkspaceMembershipResponse]

    @classmethod
    def from_memberships(
        cls,
        memberships: list[WorkspaceMembership],
    ) -> WorkspaceMembershipListResponse:
        return cls(
            items=[
                WorkspaceMembershipResponse.from_membership(membership)
                for membership in memberships
            ]
        )
