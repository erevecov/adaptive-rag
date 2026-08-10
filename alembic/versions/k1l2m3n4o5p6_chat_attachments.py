"""Add chat_attachments table.

Revision ID: k1l2m3n4o5p6
Revises: j9k0l1m2n3o4
Create Date: 2026-08-10

Adjuntos de chat subidos por usuarios: bytes en DB, ownership por
(project, user) y referencia opcional a la sesion de chat.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "k1l2m3n4o5p6"
down_revision: str | Sequence[str] | None = "j9k0l1m2n3o4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_attachments",
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
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("mime", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="ready",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('image', 'document')",
            name="chat_attachments_kind_check",
        ),
        sa.CheckConstraint(
            "status IN ('ready', 'failed')",
            name="chat_attachments_status_check",
        ),
    )
    op.create_index(
        "ix_chat_attachments_project_user",
        "chat_attachments",
        ["project_id", "user_id"],
    )
    op.create_index(
        "ix_chat_attachments_session",
        "chat_attachments",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_attachments_session", table_name="chat_attachments")
    op.drop_index(
        "ix_chat_attachments_project_user",
        table_name="chat_attachments",
    )
    op.drop_table("chat_attachments")
