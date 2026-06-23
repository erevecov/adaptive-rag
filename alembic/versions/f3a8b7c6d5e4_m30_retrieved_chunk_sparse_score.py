"""m30 retrieved chunk sparse score

Revision ID: f3a8b7c6d5e4
Revises: e2a7b9c4d5f0
Create Date: 2026-06-23 00:00:00.000000

Preserva scores sparse en audit/history para dense_sparse.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a8b7c6d5e4"
down_revision: str | Sequence[str] | None = "e2a7b9c4d5f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "retrieved_chunks",
        sa.Column("sparse_score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("retrieved_chunks", "sparse_score")
