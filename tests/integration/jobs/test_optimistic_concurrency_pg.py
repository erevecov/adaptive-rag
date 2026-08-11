"""Atomic stale-version enforcement on PostgreSQL."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.db.models import JobQueue
from adaptive_rag.jobs import JobHandlerDefinition, JobRegistry, JobStateConflictError
from adaptive_rag.jobs.schedule_service import (
    CreateJobScheduleRequest,
    JobScheduleService,
)
from adaptive_rag.jobs.service import JobActor, JobService

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
ADMIN = JobActor(actor_type="user", actor_id="admin")


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _registry() -> JobRegistry:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="optimistic_probe",
            version=1,
            payload_model=Payload,
            handler=lambda _context, _payload: {},
            queue_name="system",
            allowed_scopes=frozenset({"system"}),
            allow_manual_enqueue=True,
        )
    )
    return registry


def test_queue_configuration_accepts_one_concurrent_mutation(
    job_session_factory: sessionmaker[Session],
) -> None:
    ready = Barrier(2)

    def mutate(limit: int) -> bool:
        with job_session_factory() as session:
            queue = session.get(JobQueue, "default")
            assert queue is not None
            expected_version = queue.version
            ready.wait(timeout=10)
            try:
                JobService(session=session, registry=_registry()).configure_queue(
                    queue_name="default",
                    actor=ADMIN,
                    expected_version=expected_version,
                    global_concurrency_limit=limit,
                    now=NOW,
                )
                session.commit()
            except JobStateConflictError:
                session.rollback()
                return False
            return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        accepted = list(executor.map(mutate, (2, 3)))

    assert sorted(accepted) == [False, True]


def test_schedule_pause_accepts_one_concurrent_version(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = _registry()
    with job_session_factory() as session:
        schedule = JobScheduleService(session=session, registry=registry).create(
            CreateJobScheduleRequest(
                scope="system",
                workspace_id=None,
                name="optimistic schedule",
                job_type="optimistic_probe",
                cron_expression="0 * * * *",
            ),
            actor=ADMIN,
            now=NOW,
        )
        session.commit()
        schedule_id = schedule.id
        expected_version = schedule.version
    ready = Barrier(2)

    def pause(_index: int) -> bool:
        with job_session_factory() as session:
            service = JobScheduleService(session=session, registry=registry)
            service.get(
                schedule_id=schedule_id,
                scope="system",
                workspace_id=None,
            )
            ready.wait(timeout=10)
            try:
                service.pause(
                    schedule_id=schedule_id,
                    scope="system",
                    workspace_id=None,
                    actor=ADMIN,
                    expected_version=expected_version,
                    now=NOW,
                )
                session.commit()
            except JobStateConflictError:
                session.rollback()
                return False
            return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        accepted = list(executor.map(pause, range(2)))

    assert sorted(accepted) == [False, True]
