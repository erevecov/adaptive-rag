"""Replicated durable scheduler behavior on PostgreSQL."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.db.models import Job, JobSchedule
from adaptive_rag.jobs import JobHandlerDefinition, JobRegistry
from adaptive_rag.jobs.scheduler import JobScheduler

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


class ScheduledPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str


def _handler(_context, payload: ScheduledPayload) -> dict[str, str]:
    return {"value": payload.value}


def _registry() -> JobRegistry:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="scheduled_echo",
            version=1,
            payload_model=ScheduledPayload,
            handler=_handler,
            queue_name="system",
            allowed_scopes=frozenset({"system"}),
            allow_manual_enqueue=True,
        )
    )
    return registry


def _create_due_schedule(factory: sessionmaker[Session]) -> UUID:
    with factory() as session:
        schedule = JobSchedule(
            scope="system",
            workspace_id=None,
            name="replicated schedule",
            queue_name="system",
            job_type="scheduled_echo",
            handler_version=1,
            payload_json={"value": "scheduled"},
            cron_expression="* * * * *",
            timezone="UTC",
            misfire_policy="run_once",
            max_catch_up=10,
            next_run_at=NOW - timedelta(minutes=5),
        )
        session.add(schedule)
        session.commit()
        return schedule.id


def test_two_schedulers_create_one_job_per_occurrence(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = _registry()
    schedule_id = _create_due_schedule(job_session_factory)
    ready = Barrier(2)

    def tick(_index: int) -> int:
        ready.wait(timeout=20)
        with job_session_factory() as session:
            count = JobScheduler(session=session, registry=registry).run_once(
                now=NOW,
                batch_size=100,
            )
            session.commit()
            return count

    with ThreadPoolExecutor(max_workers=2) as executor:
        counts = list(executor.map(tick, range(2)))

    with job_session_factory() as session:
        jobs = list(session.scalars(select(Job).where(Job.schedule_id == schedule_id)))
        schedule = session.get(JobSchedule, schedule_id)
        assert schedule is not None
        assert len(jobs) == 1
        assert jobs[0].scheduled_for == NOW
        assert schedule.next_run_at > NOW
        assert schedule.last_scheduled_for == NOW
        assert (
            session.scalar(
                select(func.count(Job.id)).where(
                    Job.schedule_id == schedule_id,
                    Job.scheduled_for == NOW,
                )
            )
            == 1
        )

    assert sum(counts) == 1


def test_catch_up_is_oldest_first_and_bounded(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = _registry()
    with job_session_factory() as session:
        schedule = JobSchedule(
            scope="system",
            workspace_id=None,
            name="catch-up schedule",
            queue_name="system",
            job_type="scheduled_echo",
            handler_version=1,
            payload_json={"value": "catch-up"},
            cron_expression="* * * * *",
            timezone="UTC",
            misfire_policy="catch_up",
            max_catch_up=2,
            next_run_at=NOW - timedelta(minutes=4),
        )
        session.add(schedule)
        session.commit()
        schedule_id = schedule.id
    with job_session_factory() as session:
        count = JobScheduler(session=session, registry=registry).run_once(now=NOW)
        session.commit()

    with job_session_factory() as session:
        scheduled = list(
            session.scalars(
                select(Job.scheduled_for)
                .where(Job.schedule_id == schedule_id)
                .order_by(Job.scheduled_for)
            )
        )
    assert count == 2
    assert scheduled == [
        NOW - timedelta(minutes=4),
        NOW - timedelta(minutes=3),
    ]


def test_run_once_uses_the_latest_occurrence_beyond_expansion_limit(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = _registry()
    with job_session_factory() as session:
        schedule = JobSchedule(
            scope="system",
            workspace_id=None,
            name="long-misfire schedule",
            queue_name="system",
            job_type="scheduled_echo",
            handler_version=1,
            payload_json={"value": "latest"},
            cron_expression="* * * * *",
            timezone="UTC",
            misfire_policy="run_once",
            max_catch_up=1,
            next_run_at=NOW - timedelta(minutes=200),
        )
        session.add(schedule)
        session.commit()
        schedule_id = schedule.id

    with job_session_factory() as session:
        count = JobScheduler(session=session, registry=registry).run_once(now=NOW)
        session.commit()

    with job_session_factory() as session:
        job = session.scalar(select(Job).where(Job.schedule_id == schedule_id))
        schedule = session.get(JobSchedule, schedule_id)
        assert job is not None
        assert schedule is not None
        assert count == 1
        assert job.scheduled_for == NOW
        assert schedule.last_scheduled_for == NOW
        assert schedule.next_run_at > NOW
