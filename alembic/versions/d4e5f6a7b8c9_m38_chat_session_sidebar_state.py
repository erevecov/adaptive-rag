"""m38 chat session sidebar state

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-28 00:00:00.000000

Adds lightweight presentation state for project-scoped chat sessions.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("title", sa.Text(), nullable=True))
    op.add_column(
        "chat_sessions",
        sa.Column(
            "title_is_custom",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_chat_sessions_project_user_archived_created_at",
        "chat_sessions",
        ["project_id", "user_id", "archived_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chat_sessions_project_user_archived_created_at",
        table_name="chat_sessions",
    )
    op.drop_column("chat_sessions", "archived_at")
    op.drop_column("chat_sessions", "title_is_custom")
    op.drop_column("chat_sessions", "title")
