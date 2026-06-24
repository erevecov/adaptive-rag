"""m33 provider connections secrets

Revision ID: 7b8c9d0e1f2a
Revises: f3a8b7c6d5e4
Create Date: 2026-06-24 00:00:00.000000

Agrega provider connections globales y secrets cifrados sin scope de proyecto.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b8c9d0e1f2a"
down_revision: str | Sequence[str] | None = "f3a8b7c6d5e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_connections",
        sa.Column("connection_id", sa.String(), primary_key=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("connection_type", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=True),
        sa.Column("capabilities_json", postgresql.JSONB(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
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
        sa.CheckConstraint(
            "provider IN ('fake', 'qwen', 'local_openai_compatible')",
            name="provider_connections_provider_check",
        ),
        sa.CheckConstraint(
            "connection_type IN ('fake', 'hosted', 'local')",
            name="provider_connections_connection_type_check",
        ),
    )

    op.create_table(
        "provider_secrets",
        sa.Column(
            "connection_id",
            sa.String(),
            sa.ForeignKey("provider_connections.connection_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("secret_name", sa.String(), primary_key=True),
        sa.Column("encrypted_value", sa.LargeBinary(), nullable=False),
        sa.Column("fingerprint", sa.String(), nullable=True),
        sa.Column("last_four", sa.String(), nullable=True),
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
        sa.CheckConstraint(
            "secret_name IN ('api_key')",
            name="provider_secrets_secret_name_check",
        ),
    )


def downgrade() -> None:
    op.drop_table("provider_secrets")
    op.drop_table("provider_connections")
