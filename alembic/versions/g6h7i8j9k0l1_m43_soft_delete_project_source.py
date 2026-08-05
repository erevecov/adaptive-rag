"""m43 soft delete for projects and sources

Revision ID: g6h7i8j9k0l1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "g6h7i8j9k0l1"
down_revision: str | None = "f4a5b6c7d8e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_projects_deleted_at", "projects", ["deleted_at"])
    op.create_index("ix_sources_deleted_at", "sources", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_sources_deleted_at", table_name="sources")
    op.drop_index("ix_projects_deleted_at", table_name="projects")
    op.drop_column("sources", "deleted_at")
    op.drop_column("projects", "deleted_at")
