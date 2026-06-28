"""m36 promote dense_sparse defaults

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-28 00:00:00.000000

Promueve dense_sparse como default publico de proyectos nuevos.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "projects",
        "embedding_mode",
        existing_type=sa.String(),
        nullable=False,
        server_default=sa.text("'dense_sparse'"),
    )


def downgrade() -> None:
    op.alter_column(
        "projects",
        "embedding_mode",
        existing_type=sa.String(),
        nullable=False,
        server_default=sa.text("'dense'"),
    )
