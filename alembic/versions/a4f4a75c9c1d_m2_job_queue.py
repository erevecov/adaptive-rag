"""m2 job queue

Revision ID: a4f4a75c9c1d
Revises: 6de20037eb1f
Create Date: 2026-06-18 20:45:00.000000

Agrega jobs y job_events para persistir trabajo asincronico, auditoria,
retries y leasing basico por proyecto.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4f4a75c9c1d"
down_revision: str | Sequence[str] | None = "6de20037eb1f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "run_after",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("locked_by", sa.String(), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
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
            "status IN ('queued', 'running', 'succeeded', 'blocked', 'dead_letter')",
            name="jobs_status_check",
        ),
        sa.CheckConstraint(
            "attempts >= 0",
            name="jobs_attempts_non_negative_check",
        ),
        sa.CheckConstraint(
            "max_attempts > 0",
            name="jobs_max_attempts_positive_check",
        ),
    )
    op.create_index("ix_jobs_project_id", "jobs", ["project_id"])
    op.create_index(
        "ix_jobs_project_status_run_after_priority",
        "jobs",
        ["project_id", "status", "run_after", "priority"],
    )
    op.create_index(
        "ix_jobs_project_locked_until",
        "jobs",
        ["project_id", "locked_until"],
    )
    op.create_index(
        "ix_jobs_project_created_at",
        "jobs",
        ["project_id", "created_at"],
    )

    op.create_table(
        "job_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ("
            "'created', 'leased', 'completed', 'failed_attempt', "
            "'blocked', 'dead_lettered', 'released'"
            ")",
            name="job_events_event_type_check",
        ),
    )
    op.create_index("ix_job_events_project_id", "job_events", ["project_id"])
    op.create_index("ix_job_events_job_id", "job_events", ["job_id"])
    op.create_index(
        "ix_job_events_project_job_created_at",
        "job_events",
        ["project_id", "job_id", "created_at"],
    )
    op.create_index(
        "ix_job_events_project_event_type",
        "job_events",
        ["project_id", "event_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_events_project_event_type", table_name="job_events")
    op.drop_index("ix_job_events_project_job_created_at", table_name="job_events")
    op.drop_index("ix_job_events_job_id", table_name="job_events")
    op.drop_index("ix_job_events_project_id", table_name="job_events")
    op.drop_table("job_events")

    op.drop_index("ix_jobs_project_created_at", table_name="jobs")
    op.drop_index("ix_jobs_project_locked_until", table_name="jobs")
    op.drop_index("ix_jobs_project_status_run_after_priority", table_name="jobs")
    op.drop_index("ix_jobs_project_id", table_name="jobs")
    op.drop_table("jobs")

