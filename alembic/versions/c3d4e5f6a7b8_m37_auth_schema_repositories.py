"""m37 auth schema repositories

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-28 00:00:00.000000

Agrega usuarios locales, memberships por proyecto, ownership de chat sessions
y propuestas de conocimiento originadas desde chat.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("login", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("system_role", sa.String(), nullable=False, server_default="user"),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "system_role IN ('superadmin', 'user')",
            name="users_system_role_check",
        ),
        sa.UniqueConstraint("login", name="uq_users_login"),
    )

    op.create_table(
        "user_access_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("token_hash", name="uq_user_access_tokens_token_hash"),
    )
    op.create_index(
        "ix_user_access_tokens_user_created_at",
        "user_access_tokens",
        ["user_id", "created_at"],
    )

    op.create_table(
        "project_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'contributor', 'viewer')",
            name="project_memberships_role_check",
        ),
        sa.UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_memberships_project_user",
        ),
    )
    op.create_index(
        "ix_project_memberships_project_role",
        "project_memberships",
        ["project_id", "role"],
    )
    op.create_index(
        "ix_project_memberships_user_role",
        "project_memberships",
        ["user_id", "role"],
    )

    op.add_column(
        "chat_sessions",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_chat_sessions_project_user_created_at",
        "chat_sessions",
        ["project_id", "user_id", "created_at"],
    )

    op.create_table(
        "knowledge_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "submitted_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "origin_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "origin_message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "approved_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "reviewed_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("proposed_text", sa.Text(), nullable=False),
        sa.Column("refined_text", sa.Text(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="knowledge_proposals_status_check",
        ),
    )
    op.create_index(
        "ix_knowledge_proposals_project_status_created_at",
        "knowledge_proposals",
        ["project_id", "status", "created_at"],
    )
    op.create_index(
        "ix_knowledge_proposals_project_submitter_created_at",
        "knowledge_proposals",
        ["project_id", "submitted_by_user_id", "created_at"],
    )
    op.create_index(
        "ix_knowledge_proposals_project_origin_session",
        "knowledge_proposals",
        ["project_id", "origin_session_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_knowledge_proposals_project_origin_session",
        table_name="knowledge_proposals",
    )
    op.drop_index(
        "ix_knowledge_proposals_project_submitter_created_at",
        table_name="knowledge_proposals",
    )
    op.drop_index(
        "ix_knowledge_proposals_project_status_created_at",
        table_name="knowledge_proposals",
    )
    op.drop_table("knowledge_proposals")

    op.drop_index(
        "ix_chat_sessions_project_user_created_at",
        table_name="chat_sessions",
    )
    op.drop_column("chat_sessions", "user_id")

    op.drop_index("ix_project_memberships_user_role", table_name="project_memberships")
    op.drop_index(
        "ix_project_memberships_project_role",
        table_name="project_memberships",
    )
    op.drop_table("project_memberships")

    op.drop_index(
        "ix_user_access_tokens_user_created_at",
        table_name="user_access_tokens",
    )
    op.drop_table("user_access_tokens")

    op.drop_table("users")

