"""general PostgreSQL job platform

Revision ID: p5q6r7s8t9u0
Revises: n4o5p6q7r8s9
Create Date: 2026-08-10 00:00:00.000000

The upgrade is additive and preserves existing job/event UUIDs. Downgrade is
structural only: system-scoped or newly terminal data may need operator cleanup
before legacy NOT NULL/status constraints can be restored.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "p5q6r7s8t9u0"
down_revision: str | Sequence[str] | None = "n4o5p6q7r8s9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def _create_queue_tables() -> None:
    op.create_table(
        "job_queues",
        sa.Column("name", sa.String(length=100), primary_key=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_by_actor", sa.String(length=255), nullable=True),
        sa.Column("global_concurrency_limit", sa.Integer(), nullable=True),
        sa.Column("workspace_concurrency_limit", sa.Integer(), nullable=True),
        sa.Column(
            "default_lease_seconds",
            sa.Integer(),
            nullable=False,
            server_default="300",
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "global_concurrency_limit IS NULL OR global_concurrency_limit > 0",
            name="job_queues_global_limit_positive_check",
        ),
        sa.CheckConstraint(
            "workspace_concurrency_limit IS NULL OR workspace_concurrency_limit > 0",
            name="job_queues_workspace_limit_positive_check",
        ),
        sa.CheckConstraint(
            "default_lease_seconds >= 15 AND default_lease_seconds <= 3600",
            name="job_queues_lease_bounds_check",
        ),
        sa.CheckConstraint("version > 0", name="job_queues_version_positive_check"),
    )
    op.bulk_insert(
        sa.table("job_queues", sa.column("name", sa.String())),
        [{"name": "default"}, {"name": "ingestion"}, {"name": "system"}],
    )
    op.create_table(
        "job_queue_workspace_state",
        sa.Column(
            "queue_name",
            sa.String(length=100),
            sa.ForeignKey("job_queues.name", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("scope_key", sa.String(length=256), primary_key=True),
        sa.Column("last_claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "scope_key = 'system' OR scope_key LIKE 'workspace:%'",
            name="job_queue_workspace_state_scope_key_check",
        ),
    )


def _create_schedule_table() -> None:
    op.create_table(
        "job_schedules",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column(
            "workspace_id",
            UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "queue_name",
            sa.String(length=100),
            sa.ForeignKey("job_queues.name", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("job_type", sa.String(length=100), nullable=False),
        sa.Column("handler_version", sa.Integer(), nullable=False),
        sa.Column(
            "payload_json",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("concurrency_key", sa.String(length=255), nullable=True),
        sa.Column("cron_expression", sa.String(length=255), nullable=False),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.Column(
            "misfire_policy",
            sa.String(length=16),
            nullable=False,
            server_default="run_once",
        ),
        sa.Column("max_catch_up", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_actor_type", sa.String(length=32), nullable=True),
        sa.Column("created_by_actor_id", sa.String(length=255), nullable=True),
        sa.Column("updated_by_actor_type", sa.String(length=32), nullable=True),
        sa.Column("updated_by_actor_id", sa.String(length=255), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "(scope = 'workspace' AND workspace_id IS NOT NULL) OR "
            "(scope = 'system' AND workspace_id IS NULL)",
            name="job_schedules_scope_workspace_check",
        ),
        sa.CheckConstraint(
            "misfire_policy IN ('skip', 'run_once', 'catch_up')",
            name="job_schedules_misfire_policy_check",
        ),
        sa.CheckConstraint(
            "max_catch_up >= 1 AND max_catch_up <= 100",
            name="job_schedules_max_catch_up_bounds_check",
        ),
        sa.CheckConstraint(
            "handler_version > 0",
            name="job_schedules_handler_version_positive_check",
        ),
        sa.CheckConstraint(
            "priority >= -1000 AND priority <= 1000",
            name="job_schedules_priority_bounds_check",
        ),
        sa.CheckConstraint("version > 0", name="job_schedules_version_positive_check"),
    )
    op.create_index("ix_job_schedules_workspace_id", "job_schedules", ["workspace_id"])
    op.create_index(
        "ix_job_schedules_workspace_created",
        "job_schedules",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_job_schedules_due",
        "job_schedules",
        ["next_run_at"],
        postgresql_where=sa.text("paused_at IS NULL AND archived_at IS NULL"),
    )
    op.execute(
        """
        INSERT INTO job_schedules (
            id, scope, workspace_id, name, description, queue_name, job_type,
            handler_version, payload_json, priority, cron_expression, timezone,
            misfire_policy, max_catch_up, next_run_at,
            created_by_actor_type, created_by_actor_id,
            updated_by_actor_type, updated_by_actor_id
        ) VALUES (
            '00000000-0000-0000-0000-000000000701', 'system', NULL,
            'Daily provider model pricing sync',
            'Refresh provider model pricing metadata once per UTC day.',
            'system', 'provider_model_pricing_sync', 1, '{}'::jsonb, 0,
            '0 0 * * *', 'UTC', 'run_once', 1,
            ((date_trunc('day', now() AT TIME ZONE 'UTC') + interval '1 day')
                AT TIME ZONE 'UTC'),
            'system', 'migration', 'system', 'migration'
        )
        """
    )


def _expand_jobs() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "scope", sa.String(length=16), nullable=False, server_default="workspace"
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "queue_name",
            sa.String(length=100),
            nullable=False,
            server_default="ingestion",
        ),
    )
    op.add_column(
        "jobs",
        sa.Column("handler_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("jobs", sa.Column("result_json", JSONB, nullable=True))
    op.add_column(
        "jobs", sa.Column("idempotency_key", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "jobs",
        sa.Column("idempotency_fingerprint", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "jobs",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "jobs",
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="2"),
    )
    op.add_column("jobs", sa.Column("schedule_id", UUID, nullable=True))
    op.add_column(
        "jobs", sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "jobs", sa.Column("concurrency_key", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "jobs",
        sa.Column(
            "cancellation_requested_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "cancellation_requested_by_actor_type",
            sa.String(length=32),
            nullable=True,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "cancellation_requested_by_actor_id",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        "jobs", sa.Column("last_error_code", sa.String(length=100), nullable=True)
    )
    op.add_column("jobs", sa.Column("last_error_message", sa.Text(), nullable=True))
    op.add_column(
        "jobs", sa.Column("last_trace_id", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "jobs", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "jobs", sa.Column("version", sa.Integer(), nullable=False, server_default="1")
    )

    op.execute(
        sa.text("UPDATE jobs SET payload_json = '{}'::jsonb WHERE payload_json IS NULL")
    )
    op.execute(
        sa.text(
            "UPDATE jobs SET attempt_count = attempts, "
            "retry_count = CASE WHEN status = 'blocked' THEN 0 "
            "ELSE LEAST(attempts, max_attempts) END, "
            "max_retries = LEAST(GREATEST(max_attempts - 1, 0), 25)"
        )
    )
    op.alter_column("jobs", "workspace_id", existing_type=UUID, nullable=True)
    op.alter_column("jobs", "payload_json", existing_type=JSONB, nullable=False)
    op.drop_constraint("jobs_status_check", "jobs", type_="check")
    op.create_check_constraint(
        "jobs_status_check",
        "jobs",
        "status IN ('queued', 'running', 'succeeded', 'blocked', "
        "'dead_letter', 'cancelled')",
    )
    op.create_check_constraint(
        "jobs_scope_workspace_check",
        "jobs",
        "(scope = 'workspace' AND workspace_id IS NOT NULL) OR "
        "(scope = 'system' AND workspace_id IS NULL)",
    )
    op.create_check_constraint(
        "jobs_attempt_count_non_negative_check", "jobs", "attempt_count >= 0"
    )
    op.create_check_constraint(
        "jobs_retry_count_non_negative_check", "jobs", "retry_count >= 0"
    )
    op.create_check_constraint(
        "jobs_max_retries_bounds_check",
        "jobs",
        "max_retries >= 0 AND max_retries <= 25",
    )
    op.create_check_constraint(
        "jobs_handler_version_positive_check", "jobs", "handler_version > 0"
    )
    op.create_check_constraint(
        "jobs_priority_bounds_check", "jobs", "priority >= -1000 AND priority <= 1000"
    )
    op.create_check_constraint("jobs_version_positive_check", "jobs", "version > 0")
    op.create_check_constraint(
        "jobs_idempotency_fingerprint_check",
        "jobs",
        "(idempotency_key IS NULL AND idempotency_fingerprint IS NULL) OR "
        "(idempotency_key IS NOT NULL AND idempotency_fingerprint IS NOT NULL)",
    )
    op.create_foreign_key(
        "fk_jobs_queue_name_job_queues",
        "jobs",
        "job_queues",
        ["queue_name"],
        ["name"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_jobs_schedule_id_job_schedules",
        "jobs",
        "job_schedules",
        ["schedule_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_jobs_queue_status_run_after_priority",
        "jobs",
        ["queue_name", "status", "run_after", "priority", "created_at", "id"],
    )
    op.create_index(
        "ix_jobs_schedule_scheduled_for", "jobs", ["schedule_id", "scheduled_for"]
    )
    op.create_index(
        "uq_jobs_schedule_occurrence",
        "jobs",
        ["schedule_id", "scheduled_for"],
        unique=True,
        postgresql_where=sa.text(
            "schedule_id IS NOT NULL AND scheduled_for IS NOT NULL"
        ),
    )
    open_jobs = sa.text(
        "idempotency_key IS NOT NULL AND status IN ('queued', 'running', 'blocked')"
    )
    op.create_index(
        "uq_jobs_workspace_open_idempotency",
        "jobs",
        ["workspace_id", "job_type", "handler_version", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(f"scope = 'workspace' AND {open_jobs.text}"),
    )
    op.create_index(
        "uq_jobs_system_open_idempotency",
        "jobs",
        ["job_type", "handler_version", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(f"scope = 'system' AND {open_jobs.text}"),
    )
    op.execute(
        sa.text(
            "INSERT INTO job_queue_workspace_state "
            "(queue_name, scope_key, created_at, updated_at) "
            "SELECT DISTINCT queue_name, "
            "'workspace:' || workspace_id::text, now(), now() "
            "FROM jobs ON CONFLICT (queue_name, scope_key) DO NOTHING"
        )
    )


def _create_attempts_and_fence() -> None:
    op.create_table(
        "job_attempts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "job_id",
            UUID,
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column(
            "workspace_id",
            UUID,
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("worker_id", UUID, nullable=False),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="running"
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "heartbeat_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("progress_json", JSONB, nullable=True),
        sa.Column("progress_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'retryable_failed', 'blocked', "
            "'dead_letter', 'expired', 'cancelled', 'fenced')",
            name="job_attempts_status_check",
        ),
        sa.CheckConstraint(
            "(scope = 'workspace' AND workspace_id IS NOT NULL) OR "
            "(scope = 'system' AND workspace_id IS NULL)",
            name="job_attempts_scope_workspace_check",
        ),
        sa.CheckConstraint(
            "attempt_number > 0", name="job_attempts_attempt_number_positive_check"
        ),
        sa.UniqueConstraint(
            "job_id", "attempt_number", name="uq_job_attempts_job_attempt_number"
        ),
    )
    op.create_index("ix_job_attempts_job_id", "job_attempts", ["job_id"])
    op.create_index("ix_job_attempts_workspace_id", "job_attempts", ["workspace_id"])
    op.create_index(
        "ix_job_attempts_job_started_at", "job_attempts", ["job_id", "started_at"]
    )
    op.create_index(
        "ix_job_attempts_status_lease",
        "job_attempts",
        ["status", "lease_expires_at"],
    )
    op.create_index(
        "ix_job_attempts_worker_status", "job_attempts", ["worker_id", "status"]
    )
    op.add_column("jobs", sa.Column("current_attempt_id", UUID, nullable=True))
    op.create_foreign_key(
        "fk_jobs_current_attempt_id_job_attempts",
        "jobs",
        "job_attempts",
        ["current_attempt_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_jobs_current_attempt_id", "jobs", ["current_attempt_id"])


def _expand_events() -> None:
    op.add_column(
        "job_events",
        sa.Column(
            "scope", sa.String(length=16), nullable=False, server_default="workspace"
        ),
    )
    op.add_column("job_events", sa.Column("attempt_id", UUID, nullable=True))
    op.add_column(
        "job_events", sa.Column("actor_type", sa.String(length=32), nullable=True)
    )
    op.add_column(
        "job_events", sa.Column("actor_id", sa.String(length=255), nullable=True)
    )
    op.alter_column("job_events", "workspace_id", existing_type=UUID, nullable=True)
    op.drop_constraint("job_events_event_type_check", "job_events", type_="check")
    op.create_check_constraint(
        "job_events_event_type_check",
        "job_events",
        "event_type IN ('created', 'queued', 'leased', 'progress', 'completed', "
        "'completed_after_cancel_request', 'failed_attempt', 'retry_scheduled', "
        "'blocked', 'unblocked', 'dead_lettered', 'cancel_requested', 'cancelled', "
        "'expired', 'retried', 'released', 'scheduled', 'run_now')",
    )
    op.create_check_constraint(
        "job_events_scope_workspace_check",
        "job_events",
        "(scope = 'workspace' AND workspace_id IS NOT NULL) OR "
        "(scope = 'system' AND workspace_id IS NULL)",
    )
    op.create_foreign_key(
        "fk_job_events_attempt_id_job_attempts",
        "job_events",
        "job_attempts",
        ["attempt_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_job_events_attempt_id", "job_events", ["attempt_id"])
    op.create_index(
        "ix_job_events_job_created_at",
        "job_events",
        ["job_id", "created_at", "id"],
    )


def _create_worker_table() -> None:
    op.create_table(
        "job_workers",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("process_identity", sa.String(length=128), nullable=False),
        sa.Column("application_version", sa.String(length=64), nullable=False),
        sa.Column(
            "supported_queues",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "supported_handlers",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "heartbeat_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("draining_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shutdown_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "length(process_identity) >= 1 AND length(process_identity) <= 128",
            name="job_workers_process_identity_length_check",
        ),
    )
    op.create_index(
        "ix_job_workers_live_heartbeat",
        "job_workers",
        ["heartbeat_at"],
        postgresql_where=sa.text("shutdown_at IS NULL"),
    )


def _create_notification_trigger() -> None:
    op.execute(
        sa.text(
            "CREATE FUNCTION adaptive_rag_notify_job_insert() RETURNS trigger "
            "LANGUAGE plpgsql AS $$ BEGIN "
            "PERFORM pg_notify('adaptive_rag_jobs', NEW.queue_name); "
            "RETURN NEW; END; $$"
        )
    )
    op.execute(
        sa.text(
            "CREATE TRIGGER trg_jobs_notify_insert AFTER INSERT ON jobs "
            "FOR EACH ROW EXECUTE FUNCTION adaptive_rag_notify_job_insert()"
        )
    )


def upgrade() -> None:
    _create_queue_tables()
    _create_schedule_table()
    _expand_jobs()
    _create_attempts_and_fence()
    _expand_events()
    _create_worker_table()
    _create_notification_trigger()


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_jobs_notify_insert ON jobs"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS adaptive_rag_notify_job_insert()"))

    op.drop_index("ix_job_workers_live_heartbeat", table_name="job_workers")
    op.drop_table("job_workers")

    op.drop_index("ix_job_events_job_created_at", table_name="job_events")
    op.drop_index("ix_job_events_attempt_id", table_name="job_events")
    op.drop_constraint(
        "fk_job_events_attempt_id_job_attempts", "job_events", type_="foreignkey"
    )
    op.drop_constraint("job_events_scope_workspace_check", "job_events", type_="check")
    op.drop_constraint("job_events_event_type_check", "job_events", type_="check")
    op.create_check_constraint(
        "job_events_event_type_check",
        "job_events",
        "event_type IN ('created', 'leased', 'completed', 'failed_attempt', "
        "'blocked', 'dead_lettered', 'released', 'retried')",
    )
    op.alter_column("job_events", "workspace_id", existing_type=UUID, nullable=False)
    op.drop_column("job_events", "actor_id")
    op.drop_column("job_events", "actor_type")
    op.drop_column("job_events", "attempt_id")
    op.drop_column("job_events", "scope")

    op.drop_index("ix_jobs_current_attempt_id", table_name="jobs")
    op.drop_constraint(
        "fk_jobs_current_attempt_id_job_attempts", "jobs", type_="foreignkey"
    )
    op.drop_column("jobs", "current_attempt_id")
    op.drop_index("ix_job_attempts_worker_status", table_name="job_attempts")
    op.drop_index("ix_job_attempts_status_lease", table_name="job_attempts")
    op.drop_index("ix_job_attempts_job_started_at", table_name="job_attempts")
    op.drop_index("ix_job_attempts_workspace_id", table_name="job_attempts")
    op.drop_index("ix_job_attempts_job_id", table_name="job_attempts")
    op.drop_table("job_attempts")

    op.drop_index("uq_jobs_system_open_idempotency", table_name="jobs")
    op.drop_index("uq_jobs_workspace_open_idempotency", table_name="jobs")
    op.drop_index("uq_jobs_schedule_occurrence", table_name="jobs")
    op.drop_index("ix_jobs_schedule_scheduled_for", table_name="jobs")
    op.drop_index("ix_jobs_queue_status_run_after_priority", table_name="jobs")
    op.drop_constraint("fk_jobs_schedule_id_job_schedules", "jobs", type_="foreignkey")
    op.drop_constraint("fk_jobs_queue_name_job_queues", "jobs", type_="foreignkey")
    for constraint_name in (
        "jobs_idempotency_fingerprint_check",
        "jobs_version_positive_check",
        "jobs_priority_bounds_check",
        "jobs_handler_version_positive_check",
        "jobs_max_retries_bounds_check",
        "jobs_retry_count_non_negative_check",
        "jobs_attempt_count_non_negative_check",
        "jobs_scope_workspace_check",
    ):
        op.drop_constraint(constraint_name, "jobs", type_="check")
    op.drop_constraint("jobs_status_check", "jobs", type_="check")
    op.create_check_constraint(
        "jobs_status_check",
        "jobs",
        "status IN ('queued', 'running', 'succeeded', 'blocked', 'dead_letter')",
    )
    op.alter_column("jobs", "payload_json", existing_type=JSONB, nullable=True)
    op.alter_column("jobs", "workspace_id", existing_type=UUID, nullable=False)
    for column_name in (
        "version",
        "finished_at",
        "last_trace_id",
        "last_error_message",
        "last_error_code",
        "cancellation_requested_by_actor_id",
        "cancellation_requested_by_actor_type",
        "cancellation_requested_at",
        "concurrency_key",
        "scheduled_for",
        "schedule_id",
        "max_retries",
        "retry_count",
        "attempt_count",
        "idempotency_fingerprint",
        "idempotency_key",
        "result_json",
        "handler_version",
        "queue_name",
        "scope",
    ):
        op.drop_column("jobs", column_name)

    op.drop_index("ix_job_schedules_due", table_name="job_schedules")
    op.drop_index("ix_job_schedules_workspace_created", table_name="job_schedules")
    op.drop_index("ix_job_schedules_workspace_id", table_name="job_schedules")
    op.drop_table("job_schedules")
    op.drop_table("job_queue_workspace_state")
    op.drop_table("job_queues")
