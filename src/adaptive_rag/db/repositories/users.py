"""Repositories for local users, access tokens, and project memberships."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import (
    PROJECT_ROLE_VALUES,
    SYSTEM_ROLE_VALUES,
    ProjectMembership,
    User,
    UserAccessToken,
)
from adaptive_rag.db.models.job import utc_now


class UserRepository:
    """Persistence for local users and hash-only access tokens.

    Transactions are controlled by the caller. Methods flush but do not commit.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_user(
        self,
        *,
        login: str,
        display_name: str,
        system_role: str = "user",
        is_active: bool = True,
    ) -> User:
        normalized_login = _normalize_login(login)
        normalized_role = _normalize_supported_value(
            system_role,
            supported=SYSTEM_ROLE_VALUES,
            label="system role",
        )
        if self.get_by_login(normalized_login) is not None:
            raise ValueError("user_login_already_exists")

        user = User(
            login=normalized_login,
            display_name=_normalize_non_empty(display_name, "display_name"),
            system_role=normalized_role,
            is_active=is_active,
        )
        self._session.add(user)
        self._session.flush()
        return user

    def get_user(self, user_id: UUID) -> User | None:
        return self._session.get(User, user_id)

    def get_by_login(self, login: str) -> User | None:
        statement = select(User).where(User.login == _normalize_login(login))
        return self._session.scalars(statement).one_or_none()

    def list_users(self) -> list[User]:
        statement = select(User).order_by(User.login, User.id)
        return list(self._session.scalars(statement))

    def update_user(
        self,
        user_id: UUID,
        *,
        display_name: str | None = None,
        system_role: str | None = None,
        is_active: bool | None = None,
    ) -> User | None:
        user = self.get_user(user_id)
        if user is None:
            return None
        if display_name is not None:
            user.display_name = _normalize_non_empty(display_name, "display_name")
        if system_role is not None:
            user.system_role = _normalize_supported_value(
                system_role,
                supported=SYSTEM_ROLE_VALUES,
                label="system role",
            )
        if is_active is not None:
            user.is_active = is_active
        self._session.flush()
        return user

    def upsert_access_token(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        label: str | None = None,
        expires_at: datetime | None = None,
    ) -> UserAccessToken:
        if self.get_user(user_id) is None:
            raise ValueError("user_not_found")
        normalized_hash = _normalize_non_empty(token_hash, "token_hash")
        statement = select(UserAccessToken).where(
            UserAccessToken.token_hash == normalized_hash
        )
        token = self._session.scalars(statement).one_or_none()
        if token is None:
            token = UserAccessToken(
                user_id=user_id,
                token_hash=normalized_hash,
                label=label,
                expires_at=expires_at,
            )
            self._session.add(token)
        else:
            token.user_id = user_id
            token.label = label
            token.expires_at = expires_at
            token.revoked_at = None
        self._session.flush()
        return token

    def revoke_access_token(self, token_hash: str) -> bool:
        normalized_hash = _normalize_non_empty(token_hash, "token_hash")
        statement = select(UserAccessToken).where(
            UserAccessToken.token_hash == normalized_hash,
            UserAccessToken.revoked_at.is_(None),
        )
        token = self._session.scalars(statement).one_or_none()
        if token is None:
            return False
        token.revoked_at = utc_now()
        self._session.flush()
        return True

    def get_user_by_token_hash(self, token_hash: str) -> User | None:
        normalized_hash = _normalize_non_empty(token_hash, "token_hash")
        now = utc_now()
        statement = (
            select(User)
            .join(UserAccessToken, UserAccessToken.user_id == User.id)
            .where(
                UserAccessToken.token_hash == normalized_hash,
                UserAccessToken.revoked_at.is_(None),
            )
        )
        users = list(self._session.scalars(statement))
        for user in users:
            token_statement = select(UserAccessToken).where(
                UserAccessToken.token_hash == normalized_hash,
                UserAccessToken.user_id == user.id,
            )
            token = self._session.scalars(token_statement).one()
            if token.expires_at is None or token.expires_at > now:
                return user
        return None


class ProjectMembershipRepository:
    """Persistence for project-scoped user roles."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_membership(
        self,
        *,
        project_id: UUID,
        user_id: UUID,
        role: str,
    ) -> ProjectMembership:
        normalized_role = _normalize_supported_value(
            role,
            supported=PROJECT_ROLE_VALUES,
            label="project role",
        )
        membership = self.get_membership(project_id=project_id, user_id=user_id)
        if membership is None:
            membership = ProjectMembership(
                project_id=project_id,
                user_id=user_id,
                role=normalized_role,
            )
            self._session.add(membership)
        else:
            membership.role = normalized_role
        self._session.flush()
        return membership

    def get_membership(
        self,
        *,
        project_id: UUID,
        user_id: UUID,
    ) -> ProjectMembership | None:
        statement = select(ProjectMembership).where(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == user_id,
        )
        return self._session.scalars(statement).one_or_none()

    def list_project_members(self, project_id: UUID) -> list[ProjectMembership]:
        statement = (
            select(ProjectMembership)
            .join(User, User.id == ProjectMembership.user_id)
            .where(ProjectMembership.project_id == project_id)
            .order_by(User.login, ProjectMembership.id)
        )
        return list(self._session.scalars(statement))

    def list_user_memberships(self, user_id: UUID) -> list[ProjectMembership]:
        statement = (
            select(ProjectMembership)
            .where(ProjectMembership.user_id == user_id)
            .order_by(ProjectMembership.project_id, ProjectMembership.id)
        )
        return list(self._session.scalars(statement))

    def remove_membership(self, *, project_id: UUID, user_id: UUID) -> bool:
        membership = self.get_membership(project_id=project_id, user_id=user_id)
        if membership is None:
            return False
        self._session.delete(membership)
        self._session.flush()
        return True


def _normalize_login(value: str) -> str:
    return _normalize_non_empty(value, "login").lower()


def _normalize_non_empty(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty")
    return normalized


def _normalize_supported_value(
    value: str,
    *,
    supported: tuple[str, ...],
    label: str,
) -> str:
    normalized = value.strip().lower()
    if normalized not in supported:
        raise ValueError(f"unsupported {label}: {normalized}")
    return normalized
