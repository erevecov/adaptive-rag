"""Local users, access tokens, and project memberships for M37 RBAC."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now

SYSTEM_ROLE_VALUES = ("superadmin", "user")
PROJECT_ROLE_VALUES = ("admin", "contributor", "viewer")


class User(Base):
    """Local first-party user identity."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "system_role IN ('superadmin', 'user')",
            name="users_system_role_check",
        ),
        UniqueConstraint("login", name="uq_users_login"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    login: Mapped[str] = mapped_column(nullable=False)
    display_name: Mapped[str] = mapped_column(nullable=False)
    system_role: Mapped[str] = mapped_column(
        nullable=False, default="user", server_default="user"
    )
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserAccessToken(Base):
    """Hash-only local access token for resolving current users."""

    __tablename__ = "user_access_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_user_access_tokens_token_hash"),
        Index("ix_user_access_tokens_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(nullable=False)
    label: Mapped[str | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ProjectMembership(Base):
    """Project-scoped role assignment for a user."""

    __tablename__ = "project_memberships"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'contributor', 'viewer')",
            name="project_memberships_role_check",
        ),
        UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_memberships_project_user",
        ),
        Index("ix_project_memberships_project_role", "project_id", "role"),
        Index("ix_project_memberships_user_role", "user_id", "role"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
