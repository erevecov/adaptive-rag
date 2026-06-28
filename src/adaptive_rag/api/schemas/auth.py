"""Schemas HTTP for local users and project memberships."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from adaptive_rag.auth import CurrentPrincipal
from adaptive_rag.db.models import ProjectMembership, User


class UserCreateRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login: str
    display_name: str
    system_role: str = "user"
    access_token: str | None = None
    is_active: bool = True


class UserResponse(BaseModel):
    id: UUID
    login: str
    display_name: str
    system_role: str
    is_active: bool
    last_project_id: UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_user(cls, user: User) -> UserResponse:
        return cls(
            id=user.id,
            login=user.login,
            display_name=user.display_name,
            system_role=user.system_role,
            is_active=user.is_active,
            last_project_id=user.last_project_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class CurrentUserPreferencesRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    last_project_id: UUID | None = None


class CurrentUserResponse(BaseModel):
    id: UUID | None
    login: str
    display_name: str
    system_role: str
    is_bootstrap: bool
    last_project_id: UUID | None

    @classmethod
    def from_principal(cls, principal: CurrentPrincipal) -> CurrentUserResponse:
        return cls(
            id=principal.user_id,
            login=principal.login,
            display_name=principal.display_name,
            system_role=principal.system_role,
            is_bootstrap=principal.is_bootstrap,
            last_project_id=(
                None if principal.user is None else principal.user.last_project_id
            ),
        )


class UserListResponse(BaseModel):
    items: list[UserResponse]

    @classmethod
    def from_users(cls, users: list[User]) -> UserListResponse:
        return cls(items=[UserResponse.from_user(user) for user in users])


class ProjectMembershipUpsertRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str


class ProjectMembershipResponse(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    role: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_membership(
        cls,
        membership: ProjectMembership,
    ) -> ProjectMembershipResponse:
        return cls(
            id=membership.id,
            project_id=membership.project_id,
            user_id=membership.user_id,
            role=membership.role,
            created_at=membership.created_at,
            updated_at=membership.updated_at,
        )


class ProjectMembershipListResponse(BaseModel):
    items: list[ProjectMembershipResponse]

    @classmethod
    def from_memberships(
        cls,
        memberships: list[ProjectMembership],
    ) -> ProjectMembershipListResponse:
        return cls(
            items=[
                ProjectMembershipResponse.from_membership(membership)
                for membership in memberships
            ]
        )
