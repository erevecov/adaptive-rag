"""m18 graph projection state

Revision ID: c8d9e0f1a2b3
Revises: b7a3c9d4e5f6
Create Date: 2026-06-21 00:00:00.000000

Agrega readiness/backfill de proyeccion graph por proyecto. Postgres conserva
la fuente canonica; graph DB queda como indice derivado reconstruible.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8d9e0f1a2b3"
down_revision: str | Sequence[str] | None = "b7a3c9d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "graph_projections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("backend", sa.String(), nullable=False, server_default="neo4j"),
        sa.Column("status", sa.String(), nullable=False, server_default="disabled"),
        sa.Column("source_watermark", sa.String(), nullable=True),
        sa.Column(
            "schema_version",
            sa.String(),
            nullable=False,
            server_default="graph-store-v1",
        ),
        sa.Column(
            "extractor_version",
            sa.String(),
            nullable=False,
            server_default="graph-extractor-v1",
        ),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.UniqueConstraint(
            "project_id",
            "backend",
            name="uq_graph_projections_project_backend",
        ),
        sa.CheckConstraint(
            "backend IN ('neo4j')",
            name="graph_projections_backend_check",
        ),
        sa.CheckConstraint(
            "status IN ('disabled', 'pending_backfill', 'indexing', 'ready', "
            "'stale', 'failed')",
            name="graph_projections_status_check",
        ),
    )
    op.create_index(
        "ix_graph_projections_project_id",
        "graph_projections",
        ["project_id"],
    )
    op.create_index(
        "ix_graph_projections_project_status",
        "graph_projections",
        ["project_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_graph_projections_project_status",
        table_name="graph_projections",
    )
    op.drop_index("ix_graph_projections_project_id", table_name="graph_projections")
    op.drop_table("graph_projections")
