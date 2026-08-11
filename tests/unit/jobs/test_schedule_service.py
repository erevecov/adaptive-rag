"""Schedule validation, optimistic actions, and run-now semantics."""

from datetime import UTC, datetime

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
)
from adaptive_rag.jobs.schedule_service import (
    CreateJobScheduleRequest,
    JobScheduleService,
)
from adaptive_rag.jobs.service import JobActor

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
ACTOR = JobActor(actor_type="user", actor_id="admin")


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str


def _handler(_context, payload: Payload) -> dict[str, str]:
    return {"value": payload.value}


def _service():
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
    session.add(JobQueue(name="system"))
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="scheduled_manual",
            version=1,
            payload_model=Payload,
            handler=_handler,
            queue_name="system",
            allowed_scopes=frozenset({"system"}),
            allow_manual_enqueue=True,
        )
    )
    session.commit()
    return session, JobScheduleService(session=session, registry=registry)


def test_create_validates_and_computes_next_occurrence() -> None:
    session, service = _service()

    schedule = service.create(
        CreateJobScheduleRequest(
            scope="system",
            workspace_id=None,
            name="hourly",
            job_type="scheduled_manual",
            payload={"value": "x"},
            cron_expression="0 * * * *",
            timezone="UTC",
        ),
        actor=ACTOR,
        now=NOW,
    )

    assert schedule.next_run_at == datetime(2026, 8, 10, 13, 0, tzinfo=UTC)
    assert schedule.created_by_actor_id == "admin"
    assert session.get(JobSchedule, schedule.id) is schedule


def test_run_now_links_job_without_moving_cron_cursor() -> None:
    session, service = _service()
    schedule = service.create(
        CreateJobScheduleRequest(
            scope="system",
            workspace_id=None,
            name="hourly",
            job_type="scheduled_manual",
            payload={"value": "x"},
            cron_expression="0 * * * *",
            timezone="UTC",
        ),
        actor=ACTOR,
        now=NOW,
    )
    original_next = schedule.next_run_at

    job = service.run_now(
        schedule_id=schedule.id,
        scope="system",
        workspace_id=None,
        actor=ACTOR,
        expected_version=schedule.version,
        now=NOW,
    )

    assert job.schedule_id == schedule.id
    assert job.scheduled_for is None
    assert schedule.next_run_at == original_next


def test_pause_rejects_a_stale_version() -> None:
    _session, service = _service()
    schedule = service.create(
        CreateJobScheduleRequest(
            scope="system",
            workspace_id=None,
            name="hourly",
            job_type="scheduled_manual",
            payload={"value": "x"},
            cron_expression="0 * * * *",
            timezone="UTC",
        ),
        actor=ACTOR,
        now=NOW,
    )

    with pytest.raises(JobStateConflictError):
        service.pause(
            schedule_id=schedule.id,
            scope="system",
            workspace_id=None,
            actor=ACTOR,
            expected_version=schedule.version - 1,
            now=NOW,
        )
