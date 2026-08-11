"""Explicit job lifecycle transitions and cancellation semantics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ConfigDict

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
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
from adaptive_rag.jobs import (
    JobHandlerDefinition,
    JobRegistry,
    JobStateConflictError,
    RetryPolicy,
)
from adaptive_rag.jobs.dispatcher import JobDispatcher
from adaptive_rag.jobs.service import EnqueueJobRequest, JobActor, JobService
from adaptive_rag.jobs.transitions import JobTransitions, transition_target

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
ADMIN = JobActor(actor_type="user", actor_id="admin-1")


class EchoPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


def _echo(_context, payload: EchoPayload) -> dict[str, str]:
    return {"echo": payload.message}


def _registry() -> JobRegistry:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="transition_echo",
            version=1,
            payload_model=EchoPayload,
            handler=_echo,
            queue_name="default",
            allowed_scopes=frozenset({"system"}),
            retry_policy=RetryPolicy(
                max_retries=2,
                base_delay_seconds=10,
                max_delay_seconds=60,
            ),
        )
    )
    return registry


def _session_and_registry():
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
    session = create_session_factory(engine)()
    session.add(JobQueue(name="default"))
    session.commit()
    return session, _registry()


def _queued_job():
    session, registry = _session_and_registry()
    result = JobService(session=session, registry=registry).enqueue(
        EnqueueJobRequest.system(
            job_type="transition_echo",
            payload={"message": "run"},
            run_after=NOW,
        )
    )
    session.flush()
    return session, registry, result.job


def _running_job():
    session, registry, job = _queued_job()
    claim = JobDispatcher(
        session=session,
        registry=registry,
        queue_names=("default",),
    ).claim_next(worker_id=uuid4(), now=NOW)
    assert claim is not None
    session.flush()
    return session, registry, job, claim


def _event_types(session, job_id: UUID) -> list[str]:
    return [
        event.event_type
        for event in session.query(JobEvent)
        .filter(JobEvent.job_id == job_id)
        .order_by(JobEvent.created_at, JobEvent.id)
    ]


@pytest.mark.parametrize(
    ("start", "operation", "end"),
    [
        ("running", "complete", "succeeded"),
        ("running", "retryable_failure", "queued"),
        ("running", "block", "blocked"),
        ("running", "permanent_failure", "dead_letter"),
        ("queued", "cancel", "cancelled"),
        ("blocked", "unblock", "queued"),
        ("dead_letter", "retry", "queued"),
    ],
)
def test_allowed_transition_matrix(start: str, operation: str, end: str) -> None:
    assert transition_target(start, operation) == end


def test_running_cancel_is_request_until_handler_confirms() -> None:
    session, registry, job, _claim = _running_job()

    snapshot = JobService(session=session, registry=registry).cancel(
        scope="system",
        workspace_id=None,
        job_id=job.id,
        actor=ADMIN,
        expected_version=job.version,
        now=NOW + timedelta(seconds=1),
    )

    assert snapshot.status == "running"
    assert snapshot.cancellation_requested_at is not None
    assert snapshot.cancellation_requested_at.replace(tzinfo=UTC) == NOW + timedelta(
        seconds=1
    )
    assert _event_types(session, job.id)[-1] == "cancel_requested"


def test_completion_after_cancel_request_is_success_with_audit() -> None:
    session, registry, job, claim = _running_job()
    service = JobService(session=session, registry=registry)
    service.cancel(
        scope="system",
        workspace_id=None,
        job_id=job.id,
        actor=ADMIN,
        expected_version=job.version,
        now=NOW + timedelta(seconds=1),
    )

    completed = JobTransitions(session=session, registry=registry).complete(
        job_id=job.id,
        attempt_id=claim.attempt_id,
        result={"done": True},
        now=NOW + timedelta(seconds=2),
    )

    assert completed is True
    assert session.get(Job, job.id).status == "succeeded"
    assert _event_types(session, job.id)[-1] == "completed_after_cancel_request"


def test_retryable_failure_uses_full_jitter_and_increments_retry_count() -> None:
    session, registry, job, claim = _running_job()
    transitions = JobTransitions(
        session=session,
        registry=registry,
        random_source=lambda: 0.5,
    )

    transitioned = transitions.retryable_failure(
        job_id=job.id,
        attempt_id=claim.attempt_id,
        error="temporary",
        now=NOW,
    )

    assert transitioned is True
    assert job.status == "queued"
    assert job.retry_count == 1
    assert job.run_after == NOW + timedelta(seconds=5)


def test_block_does_not_consume_retry_budget() -> None:
    session, registry, job, claim = _running_job()

    transitioned = JobTransitions(session=session, registry=registry).block(
        job_id=job.id,
        attempt_id=claim.attempt_id,
        reason="dependency",
        now=NOW,
    )

    assert transitioned is True
    assert job.status == "blocked"
    assert job.retry_count == 0


def test_queued_cancel_is_immediate_and_audited() -> None:
    session, registry, job = _queued_job()

    snapshot = JobService(session=session, registry=registry).cancel(
        scope="system",
        workspace_id=None,
        job_id=job.id,
        actor=ADMIN,
        expected_version=job.version,
        now=NOW,
    )

    assert snapshot.status == "cancelled"
    assert _event_types(session, job.id)[-1] == "cancelled"


def test_retry_and_unblock_require_matching_state_and_version() -> None:
    session, registry, dead_job, dead_claim = _running_job()
    transitions = JobTransitions(session=session, registry=registry)
    assert transitions.dead_letter(
        job_id=dead_job.id,
        attempt_id=dead_claim.attempt_id,
        reason="permanent",
        now=NOW,
    )
    dead_job.retry_count = 2
    session.flush()
    service = JobService(session=session, registry=registry)

    with pytest.raises(JobStateConflictError):
        service.retry(
            scope="system",
            workspace_id=None,
            job_id=dead_job.id,
            actor=ADMIN,
            expected_version=dead_job.version - 1,
            now=NOW,
        )
    retried = service.retry(
        scope="system",
        workspace_id=None,
        job_id=dead_job.id,
        actor=ADMIN,
        expected_version=dead_job.version,
        now=NOW,
    )
    assert retried.status == "queued"
    assert retried.retry_count == 2

    other_session, other_registry, blocked_job, blocked_claim = _running_job()
    assert JobTransitions(session=other_session, registry=other_registry).block(
        job_id=blocked_job.id,
        attempt_id=blocked_claim.attempt_id,
        reason="dependency",
        now=NOW,
    )
    unblocked = JobService(
        session=other_session,
        registry=other_registry,
    ).unblock(
        scope="system",
        workspace_id=None,
        job_id=blocked_job.id,
        actor=ADMIN,
        expected_version=blocked_job.version,
        now=NOW,
    )
    assert unblocked.status == "queued"
    assert _event_types(other_session, blocked_job.id)[-1] == "unblocked"


def test_handler_confirms_a_requested_cancellation() -> None:
    session, registry, job, claim = _running_job()
    JobService(session=session, registry=registry).cancel(
        scope="system",
        workspace_id=None,
        job_id=job.id,
        actor=ADMIN,
        expected_version=job.version,
        now=NOW,
    )

    confirmed = JobTransitions(
        session=session,
        registry=registry,
    ).confirm_cancelled(
        job_id=job.id,
        attempt_id=claim.attempt_id,
        now=NOW + timedelta(seconds=1),
    )

    assert confirmed is True
    assert job.status == "cancelled"
    assert _event_types(session, job.id)[-1] == "cancelled"


def test_stale_attempt_is_rejected_and_audited() -> None:
    session, registry, job, claim = _running_job()
    job.status = "queued"
    job.current_attempt_id = None
    session.flush()

    completed = JobTransitions(session=session, registry=registry).complete(
        job_id=job.id,
        attempt_id=claim.attempt_id,
        result={"done": True},
        now=NOW + timedelta(seconds=1),
    )

    assert completed is False
    assert job.status == "queued"
    assert "fenced_write_rejected" in _event_types(session, job.id)
