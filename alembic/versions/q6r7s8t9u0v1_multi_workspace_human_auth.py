"""multi-workspace human authentication and email identity

Revision ID: q6r7s8t9u0v1
Revises: p5q6r7s8t9u0
Create Date: 2026-08-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "q6r7s8t9u0v1"
down_revision: str | Sequence[str] | None = "p5q6r7s8t9u0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.drop_constraint("uq_users_login", "users", type_="unique")
    op.alter_column("users", "login", new_column_name="email")
    # Existing deployments already used email-shaped logins. Canonicalize them
    # before reinstating uniqueness; collisions intentionally fail migration
    # instead of silently merging identities.
    op.execute("UPDATE users SET email = lower(btrim(email))")
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    op.create_table(
        "user_password_credentials",
        sa.Column(
            "user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=80), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=80), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("token_hash", name="uq_user_sessions_token_hash"),
    )
    op.create_index(
        "ix_user_sessions_user_revoked", "user_sessions", ["user_id", "revoked_at"]
    )
    op.create_index(
        "ix_user_sessions_expires_at", "user_sessions", ["expires_at"]
    )

    op.create_table(
        "login_attempts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("email_hash", sa.String(length=80), nullable=False),
        sa.Column("ip_hash", sa.String(length=80), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_login_attempts_email_attempted",
        "login_attempts",
        ["email_hash", "attempted_at"],
    )
    op.create_index(
        "ix_login_attempts_ip_attempted",
        "login_attempts",
        ["ip_hash", "attempted_at"],
    )
    op.create_index(
        "ix_login_attempts_attempted_at", "login_attempts", ["attempted_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_login_attempts_attempted_at", table_name="login_attempts")
    op.drop_index("ix_login_attempts_ip_attempted", table_name="login_attempts")
    op.drop_index("ix_login_attempts_email_attempted", table_name="login_attempts")
    op.drop_table("login_attempts")

    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_revoked", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_table("user_password_credentials")

    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.alter_column("users", "email", new_column_name="login")
    op.create_unique_constraint("uq_users_login", "users", ["login"])
