"""m3 dense embedding metadata

Revision ID: d3f6d8a1a9b2
Revises: a4f4a75c9c1d
Create Date: 2026-06-19 00:55:00.000000

Agrega metadata reproducible para embeddings densos persistidos en chunks.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3f6d8a1a9b2"
down_revision: str | Sequence[str] | None = "a4f4a75c9c1d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chunks",
        sa.Column("embedding_metadata", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chunks", "embedding_metadata")
