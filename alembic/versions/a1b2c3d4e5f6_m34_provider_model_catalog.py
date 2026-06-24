"""m34 provider model catalog

Revision ID: a1b2c3d4e5f6
Revises: 9d0e1f2a3b4c
Create Date: 2026-06-24 00:00:00.000000

Agrega catalogo global de modelos descubiertos por provider connection.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "9d0e1f2a3b4c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_model_catalog",
        sa.Column(
            "connection_id",
            sa.String(),
            sa.ForeignKey("provider_connections.connection_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("model_id", sa.String(), primary_key=True),
        sa.Column("capabilities_json", postgresql.JSONB(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("pricing_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
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
    )
    op.create_index(
        "ix_provider_model_catalog_capabilities",
        "provider_model_catalog",
        ["connection_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_model_catalog_capabilities",
        table_name="provider_model_catalog",
    )
    op.drop_table("provider_model_catalog")
