"""m24 job event retried

Revision ID: e2a7b9c4d5f0
Revises: c8d9e0f1a2b3
Create Date: 2026-06-23 00:00:00.000000

Permite auditar reintentos manuales de jobs bloqueados o dead-letter.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2a7b9c4d5f0"
down_revision: str | Sequence[str] | None = "c8d9e0f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADED_EVENT_TYPES = (
    "'created', 'leased', 'completed', 'failed_attempt', "
    "'blocked', 'dead_lettered', 'released', 'retried'"
)
DOWNGRADED_EVENT_TYPES = (
    "'created', 'leased', 'completed', 'failed_attempt', "
    "'blocked', 'dead_lettered', 'released'"
)


def upgrade() -> None:
    op.drop_constraint(
        "job_events_event_type_check",
        "job_events",
        type_="check",
    )
    op.create_check_constraint(
        "job_events_event_type_check",
        "job_events",
        f"event_type IN ({UPGRADED_EVENT_TYPES})",
    )


def downgrade() -> None:
    op.drop_constraint(
        "job_events_event_type_check",
        "job_events",
        type_="check",
    )
    op.create_check_constraint(
        "job_events_event_type_check",
        "job_events",
        f"event_type IN ({DOWNGRADED_EVENT_TYPES})",
    )
