"""Allow chat_sessions.status = canceled.

Revision ID: j9k0l1m2n3o4
Revises: i8j9k0l1m2n3
Create Date: 2026-08-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "j9k0l1m2n3o4"
down_revision: str | None = "i8j9k0l1m2n3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("chat_sessions_status_check", "chat_sessions", type_="check")
    op.create_check_constraint(
        "chat_sessions_status_check",
        "chat_sessions",
        "status IN ('running', 'succeeded', 'failed', 'canceled')",
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE chat_sessions SET status = 'failed' WHERE status = 'canceled'"
        )
    )
    op.drop_constraint("chat_sessions_status_check", "chat_sessions", type_="check")
    op.create_check_constraint(
        "chat_sessions_status_check",
        "chat_sessions",
        "status IN ('running', 'succeeded', 'failed')",
    )
