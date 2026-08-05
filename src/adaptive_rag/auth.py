"""Local authentication and project RBAC helpers."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from adaptive_rag.db.models import ProjectMembership, User

logger = logging.getLogger(__name__)

PROJECT_ROLE_RANK = {
    "viewer": 1,
    "contributor": 2,
    "admin": 3,
}


@dataclass(frozen=True, slots=True)
class CurrentPrincipal:
    """Authenticated local user or bootstrap superadmin principal."""

    user: User | None
    is_bootstrap: bool = False

    @property
    def user_id(self) -> UUID | None:
        return None if self.user is None else self.user.id

    @property
    def login(self) -> str:
        return "bootstrap" if self.user is None else self.user.login

    @property
    def display_name(self) -> str:
        return "Bootstrap Superadmin" if self.user is None else self.user.display_name

    @property
    def system_role(self) -> str:
        return "superadmin" if self.user is None else self.user.system_role

    @property
    def is_superadmin(self) -> bool:
        return self.is_bootstrap or self.system_role == "superadmin"


def hash_access_token(raw_token: str) -> str:
    """Return the stable hash persisted for local bearer tokens."""

    token = raw_token.strip()
    if not token:
        raise ValueError("access_token must not be empty")
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def users_exist(session: Session) -> bool:
    """Return whether any user row exists.

    Transient DB failures must not look like an empty user table: callers that
    treat ``False`` as bootstrap superadmin would fail open. Re-raise after
    best-effort rollback so the API layer can return 503.
    """
    try:
        count = session.scalar(select(func.count(User.id)))
    except OperationalError:
        session.rollback()
        logger.warning(
            "users_exist_check_failed; refusing bootstrap fail-open",
            exc_info=True,
        )
        raise
    return bool(count)


def get_project_role(
    session: Session,
    *,
    principal: CurrentPrincipal,
    project_id: UUID,
) -> str | None:
    if principal.is_superadmin:
        return "superadmin"
    if principal.user_id is None:
        return None
    statement = select(ProjectMembership.role).where(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == principal.user_id,
    )
    return session.scalar(statement)


def role_meets(role: str | None, minimum_role: str) -> bool:
    if role == "superadmin":
        return True
    if role is None:
        return False
    return PROJECT_ROLE_RANK[role] >= PROJECT_ROLE_RANK[minimum_role]
