"""retrieved_chunks.chunk_id ON DELETE SET NULL for soft-delete cascade

Revision ID: i8j9k0l1m2n3
Revises: h7i8j9k0l1m2
Create Date: 2026-08-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "i8j9k0l1m2n3"
down_revision: str | None = "h7i8j9k0l1m2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "retrieved_chunks",
        "chunk_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.drop_constraint(
        "retrieved_chunks_chunk_id_fkey",
        "retrieved_chunks",
        type_="foreignkey",
    )
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
        "retrieved_chunks_chunk_id_fkey",
        "retrieved_chunks",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "retrieved_chunks_chunk_id_fkey",
        "retrieved_chunks",
        "chunks",
        ["chunk_id"],
        ["id"],
    )
    op.alter_column(
        "retrieved_chunks",
        "chunk_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
