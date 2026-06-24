"""m33 project runtime overrides

Revision ID: 9d0e1f2a3b4c
Revises: 8c9d0e1f2a3b
Create Date: 2026-06-24 00:00:00.000000

Agrega overrides project-scoped para runtime slots y pool de modelos chat.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d0e1f2a3b4c"
down_revision: str | Sequence[str] | None = "8c9d0e1f2a3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_runtime_slot_overrides",
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
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
            name="project_runtime_slot_overrides_slot_check",
        ),
    )
    op.create_index(
        "ix_project_runtime_slot_overrides_connection_id",
        "project_runtime_slot_overrides",
        ["connection_id"],
    )

    op.create_table(
        "project_chat_models",
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
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
        "ix_project_chat_models_project_default",
        "project_chat_models",
        ["project_id", "is_default"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_chat_models_project_default",
        table_name="project_chat_models",
    )
    op.drop_table("project_chat_models")
    op.drop_index(
        "ix_project_runtime_slot_overrides_connection_id",
        table_name="project_runtime_slot_overrides",
    )
    op.drop_table("project_runtime_slot_overrides")
