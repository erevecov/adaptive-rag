"""Add vision runtime slot to slot check constraints.

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2026-08-10

Amplia los CheckConstraints de slot en runtime_slot_defaults y
project_runtime_slot_overrides para aceptar el slot "vision". En SQLite el
constraint se recrea via batch_alter_table (recreate de tabla).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "l2m3n4o5p6q7"
down_revision: str | Sequence[str] | None = "k1l2m3n4o5p6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SLOT_CHECK_WITH_VISION = (
    "slot IN ('chat', 'dense_embedding', 'sparse_embedding', "
    "'rerank', 'contextualization', 'vision')"
)
_SLOT_CHECK_WITHOUT_VISION = (
    "slot IN ('chat', 'dense_embedding', 'sparse_embedding', "
    "'rerank', 'contextualization')"
)


def upgrade() -> None:
    with op.batch_alter_table("runtime_slot_defaults") as batch_op:
        batch_op.drop_constraint("runtime_slot_defaults_slot_check", type_="check")
        batch_op.create_check_constraint(
            "runtime_slot_defaults_slot_check",
            _SLOT_CHECK_WITH_VISION,
        )
    with op.batch_alter_table("project_runtime_slot_overrides") as batch_op:
        batch_op.drop_constraint(
            "project_runtime_slot_overrides_slot_check",
            type_="check",
        )
        batch_op.create_check_constraint(
            "project_runtime_slot_overrides_slot_check",
            _SLOT_CHECK_WITH_VISION,
        )


def downgrade() -> None:
    with op.batch_alter_table("project_runtime_slot_overrides") as batch_op:
        batch_op.drop_constraint(
            "project_runtime_slot_overrides_slot_check",
            type_="check",
        )
        batch_op.create_check_constraint(
            "project_runtime_slot_overrides_slot_check",
            _SLOT_CHECK_WITHOUT_VISION,
        )
    with op.batch_alter_table("runtime_slot_defaults") as batch_op:
        batch_op.drop_constraint("runtime_slot_defaults_slot_check", type_="check")
        batch_op.create_check_constraint(
            "runtime_slot_defaults_slot_check",
            _SLOT_CHECK_WITHOUT_VISION,
        )
