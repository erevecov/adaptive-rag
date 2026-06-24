"""m33 global slot defaults

Revision ID: 8c9d0e1f2a3b
Revises: 7b8c9d0e1f2a
Create Date: 2026-06-24 00:00:00.000000

Agrega defaults globales por runtime slot fijo y pool global de modelos chat.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c9d0e1f2a3b"
down_revision: str | Sequence[str] | None = "7b8c9d0e1f2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runtime_slot_defaults",
        sa.Column("slot", sa.String(), primary_key=True),
        sa.Column(
            "connection_id",
            sa.String(),
            sa.ForeignKey("provider_connections.connection_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("parameters_json", postgresql.JSONB(), nullable=True),
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
            "slot IN ('chat', 'dense_embedding', 'sparse_embedding', "
            "'rerank', 'contextualization')",
            name="runtime_slot_defaults_slot_check",
        ),
    )
    op.create_index(
        "ix_runtime_slot_defaults_connection_id",
        "runtime_slot_defaults",
        ["connection_id"],
    )

    op.create_table(
        "global_chat_models",
        sa.Column(
            "connection_id",
            sa.String(),
            sa.ForeignKey("provider_connections.connection_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("model_id", sa.String(), primary_key=True),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("parameters_json", postgresql.JSONB(), nullable=True),
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
        "ix_global_chat_models_default",
        "global_chat_models",
        ["is_default"],
    )


def downgrade() -> None:
    op.drop_index("ix_global_chat_models_default", table_name="global_chat_models")
    op.drop_table("global_chat_models")
    op.drop_index(
        "ix_runtime_slot_defaults_connection_id",
        table_name="runtime_slot_defaults",
    )
    op.drop_table("runtime_slot_defaults")
