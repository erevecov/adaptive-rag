"""m38 chat retrieval settings

Revision ID: f4a5b6c7d8e9
Revises: e5f6a7b8c9d0
Create Date: 2026-06-28 00:00:00.000000

Stores global and project-scoped chat retrieval/rerank limits.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4a5b6c7d8e9"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "global_chat_retrieval_settings",
        sa.Column("id", sa.Integer(), server_default="1", nullable=False),
        sa.Column("retrieval_limit", sa.Integer(), server_default="5", nullable=False),
        sa.Column(
            "rerank_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "rerank_candidate_limit",
            sa.Integer(),
            server_default="10",
            nullable=False,
        ),
        sa.Column("max_limit", sa.Integer(), server_default="50", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("id = 1", name="global_chat_retrieval_settings_singleton"),
        sa.CheckConstraint(
            "retrieval_limit >= 1 AND retrieval_limit <= max_limit",
            name="global_chat_retrieval_settings_retrieval_limit_check",
        ),
        sa.CheckConstraint(
            "rerank_candidate_limit >= 1 AND rerank_candidate_limit <= max_limit",
            name="global_chat_retrieval_settings_candidate_limit_check",
        ),
        sa.CheckConstraint(
            "NOT rerank_enabled OR rerank_candidate_limit >= retrieval_limit",
            name="global_chat_retrieval_settings_rerank_window_check",
        ),
        sa.CheckConstraint(
            "max_limit = 50",
            name="global_chat_retrieval_settings_max_limit_check",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.bulk_insert(
        sa.table(
            "global_chat_retrieval_settings",
            sa.column("id", sa.Integer()),
            sa.column("retrieval_limit", sa.Integer()),
            sa.column("rerank_enabled", sa.Boolean()),
            sa.column("rerank_candidate_limit", sa.Integer()),
            sa.column("max_limit", sa.Integer()),
        ),
        [
            {
                "id": 1,
                "retrieval_limit": 5,
                "rerank_enabled": True,
                "rerank_candidate_limit": 10,
                "max_limit": 50,
            }
        ],
    )
    op.create_table(
        "project_chat_retrieval_settings",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("retrieval_limit", sa.Integer(), nullable=False),
        sa.Column("rerank_enabled", sa.Boolean(), nullable=False),
        sa.Column("rerank_candidate_limit", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "retrieval_limit >= 1 AND retrieval_limit <= 50",
            name="project_chat_retrieval_settings_retrieval_limit_check",
        ),
        sa.CheckConstraint(
            "rerank_candidate_limit >= 1 AND rerank_candidate_limit <= 50",
            name="project_chat_retrieval_settings_candidate_limit_check",
        ),
        sa.CheckConstraint(
            "NOT rerank_enabled OR rerank_candidate_limit >= retrieval_limit",
            name="project_chat_retrieval_settings_rerank_window_check",
        ),
        sa.PrimaryKeyConstraint("project_id"),
    )


def downgrade() -> None:
    op.drop_table("project_chat_retrieval_settings")
    op.drop_table("global_chat_retrieval_settings")
