"""m43 soft delete for projects and sources

Revision ID: g6h7i8j9k0l1
Revises: f4a5b6c7d8e9
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
    # Source soft-delete cascades chunk removal; keep citation audit rows by
    # nulling the chunk reference instead of blocking the delete.
    op.drop_constraint(
        "retrieved_chunks_chunk_id_fkey", "retrieved_chunks", type_="foreignkey"
    )
    op.alter_column("retrieved_chunks", "chunk_id", nullable=True)
    op.create_foreign_key(
        "retrieved_chunks_chunk_id_fkey",
        "retrieved_chunks",
        "chunks",
        ["chunk_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "retrieved_chunks_chunk_id_fkey", "retrieved_chunks", type_="foreignkey"
    )
    op.execute("DELETE FROM retrieved_chunks WHERE chunk_id IS NULL")
    op.alter_column("retrieved_chunks", "chunk_id", nullable=False)
    op.create_foreign_key(
        "retrieved_chunks_chunk_id_fkey",
        "retrieved_chunks",
        "chunks",
        ["chunk_id"],
        ["id"],
    )
    op.drop_index("ix_sources_deleted_at", table_name="sources")
    op.drop_index("ix_projects_deleted_at", table_name="projects")
    op.drop_column("sources", "deleted_at")
    op.drop_column("projects", "deleted_at")
