"""Fail-closed database revision checks for process startup."""

from __future__ import annotations

from sqlalchemy import Engine, inspect, text

REQUIRED_DATABASE_REVISION = "p5q6r7s8t9u0"
REQUIRED_DATABASE_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "jobs": (
        "id",
        "scope",
        "queue_name",
        "job_type",
        "handler_version",
        "status",
        "run_after",
        "current_attempt_id",
        "version",
    ),
    "job_attempts": ("id", "job_id", "status", "lease_expires_at"),
    "job_events": ("id", "job_id", "scope", "event_type", "attempt_id"),
    "job_queues": ("name", "default_lease_seconds", "version"),
    "job_queue_workspace_state": ("queue_name", "scope_key", "last_claimed_at"),
    "job_schedules": ("id", "scope", "next_run_at", "version"),
    "job_workers": ("id", "heartbeat_at", "draining_at", "shutdown_at"),
}


def assert_database_schema_current(engine: Engine) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "alembic_version" not in table_names:
        raise RuntimeError(
            "database schema is not initialized; run alembic upgrade head"
        )
    with engine.connect() as connection:
        revisions = set(
            connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalars()
        )
    if not revisions:
        raise RuntimeError("database schema has no Alembic revision")

    missing: list[str] = []
    for table_name, required_columns in REQUIRED_DATABASE_CAPABILITIES.items():
        if table_name not in table_names:
            missing.append(table_name)
            continue
        actual_columns = {
            str(column["name"]) for column in inspector.get_columns(table_name)
        }
        missing.extend(
            f"{table_name}.{column_name}"
            for column_name in required_columns
            if column_name not in actual_columns
        )
    if missing:
        found = ",".join(sorted(revisions))
        raise RuntimeError(
            "missing required database capabilities: "
            f"{','.join(missing)}; baseline={REQUIRED_DATABASE_REVISION} "
            f"found={found}; "
            "run alembic upgrade head"
        )


__all__ = [
    "REQUIRED_DATABASE_CAPABILITIES",
    "REQUIRED_DATABASE_REVISION",
    "assert_database_schema_current",
]
