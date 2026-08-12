"""Repositories for local users, access tokens, and workspace memberships."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from adaptive_rag.db.models import (
    SYSTEM_ROLE_VALUES,
    WORKSPACE_ROLE_VALUES,
    LoginAttempt,
    User,
    UserAccessToken,
    UserPasswordCredential,
    UserSession,
    WorkspaceMembership,
)
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.security.human_auth import normalize_email


class UserRepository:
    """Persistence for local users and hash-only access tokens.

    Transactions are controlled by the caller. Methods flush but do not commit.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_user(
        self,
        *,
        email: str,
        display_name: str,
        system_role: str = "user",
        is_active: bool = True,
    ) -> User:
        normalized_email = normalize_email(email)
        normalized_role = _normalize_supported_value(
            system_role,
            supported=SYSTEM_ROLE_VALUES,
            label="system role",
        )
        if self.get_by_email(normalized_email) is not None:
            raise ValueError("email_already_exists")

        user = User(
            email=normalized_email,
            display_name=_normalize_non_empty(display_name, "display_name"),
            system_role=normalized_role,
            is_active=is_active,
        )
        self._session.add(user)
        self._session.flush()
        return user

    def lock_bootstrap_creation(self) -> None:
        """Serialize first-user setup on PostgreSQL, including an empty table."""

        if self._session.get_bind().dialect.name == "postgresql":
            self._session.execute(
                select(func.pg_advisory_xact_lock(7_328_451_901_337_421))
            )

    def lock_superadmin_invariant(self) -> None:
        """Serialize operations that could remove global superadmin authority."""

        if self._session.get_bind().dialect.name == "postgresql":
            self._session.execute(
                select(func.pg_advisory_xact_lock(7_328_451_901_337_422))
            )

    def get_user(self, user_id: UUID) -> User | None:
        return self._session.get(User, user_id)

    def get_user_for_update(self, user_id: UUID) -> User | None:
        statement = select(User).where(User.id == user_id).with_for_update()
        return self._session.scalars(statement).one_or_none()

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == normalize_email(email))
        return self._session.scalars(statement).one_or_none()

    def list_users(self) -> list[User]:
        statement = select(User).order_by(User.email, User.id)
        return list(self._session.scalars(statement))

    def update_user(
        self,
        user_id: UUID,
        *,
        email: str | None = None,
        display_name: str | None = None,
        system_role: str | None = None,
        is_active: bool | None = None,
        last_workspace_id: UUID | None = None,
    ) -> User | None:
        user = self.get_user(user_id)
        if user is None:
            return None
        if email is not None:
            normalized_email = normalize_email(email)
            existing = self.get_by_email(normalized_email)
            if existing is not None and existing.id != user_id:
                raise ValueError("email_already_exists")
            user.email = normalized_email
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
        if last_workspace_id is not None:
            user.last_workspace_id = last_workspace_id
        self._session.flush()
        return user

    def list_active_superadmins_for_update(self) -> list[User]:
        statement = (
            select(User)
            .where(User.system_role == "superadmin", User.is_active.is_(True))
            .order_by(User.id)
            .with_for_update()
        )
        return list(self._session.scalars(statement))

    def update_last_workspace_id(
        self,
        user_id: UUID,
        *,
        last_workspace_id: UUID | None,
    ) -> User | None:
        user = self.get_user(user_id)
        if user is None:
            return None
        user.last_workspace_id = last_workspace_id
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


class HumanAuthRepository:
    """Persistence for local passwords and browser sessions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_credential(self, user_id: UUID) -> UserPasswordCredential | None:
        return self._session.get(UserPasswordCredential, user_id)

    def set_password(
        self,
        *,
        user_id: UUID,
        password_hash: str,
        must_change_password: bool,
        password_changed_at: datetime | None = None,
    ) -> UserPasswordCredential:
        if self._session.get(User, user_id) is None:
            raise ValueError("user_not_found")
        credential = self.get_credential(user_id)
        if credential is None:
            credential = UserPasswordCredential(user_id=user_id)
            self._session.add(credential)
        credential.password_hash = _normalize_non_empty(password_hash, "password_hash")
        credential.must_change_password = must_change_password
        credential.password_changed_at = password_changed_at
        self._session.flush()
        return credential

    def create_session(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        csrf_token_hash: str,
        now: datetime,
        expires_at: datetime,
    ) -> UserSession:
        if self._session.get(User, user_id) is None:
            raise ValueError("user_not_found")
        human_session = UserSession(
            user_id=user_id,
            token_hash=_normalize_non_empty(token_hash, "token_hash"),
            csrf_token_hash=_normalize_non_empty(csrf_token_hash, "csrf_token_hash"),
            last_seen_at=now,
            expires_at=expires_at,
        )
        self._session.add(human_session)
        self._session.flush()
        return human_session

    def get_active_session(
        self,
        *,
        token_hash: str,
        now: datetime,
        idle_timeout: timedelta,
        touch: bool = True,
    ) -> UserSession | None:
        statement = (
            select(UserSession)
            .join(User, User.id == UserSession.user_id)
            .where(
                UserSession.token_hash == token_hash,
                UserSession.revoked_at.is_(None),
                User.is_active.is_(True),
            )
        )
        human_session = self._session.scalars(statement).one_or_none()
        if human_session is None:
            return None
        expires_at = _as_utc(human_session.expires_at)
        last_seen_at = _as_utc(human_session.last_seen_at)
        if expires_at <= now or last_seen_at + idle_timeout <= now:
            human_session.revoked_at = now
            self._session.flush()
            return None
        if touch:
            human_session.last_seen_at = now
            self._session.flush()
        return human_session

    def get_session(self, session_id: UUID) -> UserSession | None:
        return self._session.get(UserSession, session_id)

    def rotate_csrf_token(self, session_id: UUID, *, csrf_token_hash: str) -> bool:
        human_session = self.get_session(session_id)
        if human_session is None or human_session.revoked_at is not None:
            return False
        human_session.csrf_token_hash = _normalize_non_empty(
            csrf_token_hash, "csrf_token_hash"
        )
        self._session.flush()
        return True

    def revoke_session(self, session_id: UUID, *, now: datetime | None = None) -> bool:
        human_session = self.get_session(session_id)
        if human_session is None or human_session.revoked_at is not None:
            return False
        human_session.revoked_at = now or utc_now()
        self._session.flush()
        return True

    def revoke_user_sessions(
        self,
        user_id: UUID,
        *,
        except_session_id: UUID | None = None,
        now: datetime | None = None,
    ) -> int:
        statement = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
        )
        if except_session_id is not None:
            statement = statement.where(UserSession.id != except_session_id)
        sessions = list(self._session.scalars(statement))
        revoked_at = now or utc_now()
        for human_session in sessions:
            human_session.revoked_at = revoked_at
        self._session.flush()
        return len(sessions)

    def lock_login_throttle(self, *, email_hash: str, ip_hash: str) -> None:
        """Serialize login throttle check+record for the same email/IP buckets.

        PostgreSQL advisory locks close the count-before-insert race that would
        otherwise let concurrent attempts overshoot the configured thresholds.
        Non-PostgreSQL dialects (unit tests on SQLite) are a no-op.
        """

        if self._session.get_bind().dialect.name != "postgresql":
            return
        for namespace, value in (
            ("login-email", email_hash),
            ("login-ip", ip_hash),
        ):
            lock_id = _advisory_lock_id(namespace, value)
            self._session.execute(select(func.pg_advisory_xact_lock(lock_id)))

    def is_login_rate_limited(
        self,
        *,
        email_hash: str,
        ip_hash: str,
        since: datetime,
        max_email_attempts: int,
        max_ip_attempts: int,
    ) -> bool:
        # Failures are bucketed by (email, IP) so a remote attacker cannot
        # lock out a chosen account from unrelated networks. A separate per-IP
        # ceiling still blocks single-source spraying across many emails.
        pair_count = self._session.scalar(
            select(func.count(LoginAttempt.id)).where(
                LoginAttempt.email_hash == email_hash,
                LoginAttempt.ip_hash == ip_hash,
                LoginAttempt.succeeded.is_(False),
                LoginAttempt.attempted_at >= since,
            )
        )
        ip_count = self._session.scalar(
            select(func.count(LoginAttempt.id)).where(
                LoginAttempt.ip_hash == ip_hash,
                LoginAttempt.succeeded.is_(False),
                LoginAttempt.attempted_at >= since,
            )
        )
        return bool(
            (pair_count or 0) >= max_email_attempts
            or (ip_count or 0) >= max_ip_attempts
        )

    def record_login_attempt(
        self,
        *,
        email_hash: str,
        ip_hash: str,
        succeeded: bool,
        attempted_at: datetime,
    ) -> LoginAttempt:
        attempt = LoginAttempt(
            email_hash=_normalize_non_empty(email_hash, "email_hash"),
            ip_hash=_normalize_non_empty(ip_hash, "ip_hash"),
            succeeded=succeeded,
            attempted_at=attempted_at,
        )
        self._session.add(attempt)
        self._session.flush()
        return attempt

    def delete_login_attempts_before(self, cutoff: datetime) -> int:
        # synchronize_session=False avoids ORM evaluator comparing SQLite-naive
        # identity-map datetimes with an aware cutoff during bulk delete.
        result = self._session.execute(
            delete(LoginAttempt)
            .where(LoginAttempt.attempted_at < cutoff)
            .execution_options(synchronize_session=False)
        )
        return int(cast(CursorResult[Any], result).rowcount or 0)


class WorkspaceMembershipRepository:
    """Persistence for workspace-scoped user roles."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_membership(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        role: str,
    ) -> WorkspaceMembership:
        normalized_role = _normalize_supported_value(
            role,
            supported=WORKSPACE_ROLE_VALUES,
            label="workspace role",
        )
        membership = self.get_membership(workspace_id=workspace_id, user_id=user_id)
        if membership is None:
            membership = WorkspaceMembership(
                workspace_id=workspace_id,
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
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMembership | None:
        statement = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
        return self._session.scalars(statement).one_or_none()

    def get_membership_for_update(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMembership | None:
        statement = (
            select(WorkspaceMembership)
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user_id,
            )
            .with_for_update()
        )
        return self._session.scalars(statement).one_or_none()

    def list_active_workspace_admins_for_update(
        self, workspace_id: UUID
    ) -> list[WorkspaceMembership]:
        statement = (
            select(WorkspaceMembership)
            .join(User, User.id == WorkspaceMembership.user_id)
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.role == "admin",
                User.is_active.is_(True),
            )
            .order_by(WorkspaceMembership.id)
            .with_for_update()
        )
        return list(self._session.scalars(statement))

    def list_workspace_members(self, workspace_id: UUID) -> list[WorkspaceMembership]:
        statement = (
            select(WorkspaceMembership)
            .join(User, User.id == WorkspaceMembership.user_id)
            .where(WorkspaceMembership.workspace_id == workspace_id)
            .order_by(User.email, WorkspaceMembership.id)
        )
        return list(self._session.scalars(statement))

    def list_user_memberships(self, user_id: UUID) -> list[WorkspaceMembership]:
        statement = (
            select(WorkspaceMembership)
            .where(WorkspaceMembership.user_id == user_id)
            .order_by(WorkspaceMembership.workspace_id, WorkspaceMembership.id)
        )
        return list(self._session.scalars(statement))

    def remove_membership(self, *, workspace_id: UUID, user_id: UUID) -> bool:
        membership = self.get_membership(workspace_id=workspace_id, user_id=user_id)
        if membership is None:
            return False
        self._session.delete(membership)
        self._session.flush()
        return True


def _advisory_lock_id(namespace: str, key: str) -> int:
    digest = hashlib.sha256(f"{namespace}:{key}".encode()).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF


def _normalize_non_empty(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty")
    return normalized


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


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
