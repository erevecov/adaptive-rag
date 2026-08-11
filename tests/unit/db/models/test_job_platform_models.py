"""Behavioral tests for the general PostgreSQL job-platform mappings."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    JOB_ATTEMPT_STATUS_VALUES,
    JOB_MISFIRE_POLICY_VALUES,
    JOB_SCOPE_VALUES,
    JOB_STATUS_VALUES,
    Job,
    JobAttempt,
    JobEvent,
    JobQueue,
    JobQueueWorkspaceState,
    JobSchedule,
    JobWorker,
    Workspace,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Workspace.__table__,
            JobQueue.__table__,
            JobSchedule.__table__,
            Job.__table__,
            JobAttempt.__table__,
            JobEvent.__table__,
            JobQueueWorkspaceState.__table__,
            JobWorker.__table__,
        ],
    )
    return create_session_factory(engine)()


def test_system_job_persists_without_a_synthetic_workspace() -> None:
    session = _make_session()
    session.add(JobQueue(name="system"))
    job = Job(
        scope="system",
        workspace_id=None,
        queue_name="system",
        job_type="provider_model_pricing_sync",
        handler_version=1,
        payload_json={},
    )
    session.add(job)
    session.commit()

    assert isinstance(job.id, UUID)
    assert job.status == "queued"
    assert job.attempt_count == 0
    assert job.retry_count == 0
    assert job.max_retries == 2
    assert job.version == 1


def test_workspace_scope_rejects_a_missing_workspace() -> None:
    session = _make_session()
    session.add(JobQueue(name="ingestion"))
    session.add(
        Job(
            scope="workspace",
            workspace_id=None,
            queue_name="ingestion",
            job_type="ingest_source",
            payload_json={},
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_attempt_uuid_is_created_as_the_fencing_token() -> None:
    session = _make_session()
    session.add(JobQueue(name="system"))
    job = Job(
        scope="system",
        queue_name="system",
        job_type="echo",
        payload_json={},
    )
    session.add(job)
    session.flush()
    worker_id = uuid4()
    attempt = JobAttempt(
        job_id=job.id,
        scope="system",
        workspace_id=None,
        attempt_number=1,
        worker_id=worker_id,
        lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    session.add(attempt)
    session.commit()

    assert isinstance(attempt.id, UUID)
    assert attempt.status == "running"
    assert attempt.worker_id == worker_id
    assert attempt.heartbeat_at is not None


def test_queue_schedule_worker_and_dispatch_state_defaults_persist() -> None:
    session = _make_session()
    queue = JobQueue(name="default")
    schedule = JobSchedule(
        scope="system",
        name="daily-echo",
        queue_name="default",
        job_type="echo",
        handler_version=1,
        payload_json={"message": "hello"},
        cron_expression="0 0 * * *",
        timezone="UTC",
        next_run_at=datetime(2026, 8, 11, tzinfo=UTC),
    )
    state = JobQueueWorkspaceState(queue_name="default", scope_key="system")
    worker = JobWorker(
        process_identity="host:123",
        application_version="test",
        supported_queues=["default"],
        supported_handlers=["echo@1"],
    )
    session.add_all([queue, schedule, state, worker])
    session.commit()

    assert queue.default_lease_seconds == 300
    assert queue.version == 1
    assert schedule.misfire_policy == "run_once"
    assert schedule.max_catch_up == 1
    assert schedule.version == 1
    assert state.last_claimed_at is None
    assert worker.draining_at is None
    assert worker.shutdown_at is None


def test_platform_constants_and_constraints_cover_canonical_states() -> None:
    assert JOB_SCOPE_VALUES == ("workspace", "system")
    assert set(JOB_STATUS_VALUES) == {
        "queued",
        "running",
        "succeeded",
        "blocked",
        "dead_letter",
        "cancelled",
    }
    assert "expired" in JOB_ATTEMPT_STATUS_VALUES
    assert JOB_MISFIRE_POLICY_VALUES == ("skip", "run_once", "catch_up")

    job_constraints = {
        constraint.name for constraint in inspect(Job).local_table.constraints
    }
    queue_constraints = {
        constraint.name for constraint in inspect(JobQueue).local_table.constraints
    }
    assert "jobs_scope_workspace_check" in job_constraints
    assert "jobs_retry_count_non_negative_check" in job_constraints
    assert "jobs_priority_bounds_check" in job_constraints
    assert "job_queues_lease_bounds_check" in queue_constraints


def test_system_event_carries_scope_without_workspace() -> None:
    session = _make_session()
    session.add(JobQueue(name="system"))
    job = Job(
        scope="system",
        queue_name="system",
        job_type="echo",
        payload_json={},
    )
    session.add(job)
    session.flush()
    event = JobEvent(
        job_id=job.id,
        scope="system",
        workspace_id=None,
        event_type="created",
        extra_metadata={"source": "test"},
    )
    session.add(event)
    session.commit()

    assert event.scope == "system"
    assert event.workspace_id is None
