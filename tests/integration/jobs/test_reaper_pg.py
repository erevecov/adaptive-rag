"""Expired-attempt recovery races on PostgreSQL."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.db.models import Job, JobAttempt, JobEvent
from adaptive_rag.jobs import JobHandlerDefinition, JobRegistry, RetryPolicy
from adaptive_rag.jobs.dispatcher import JobDispatcher
from adaptive_rag.jobs.reaper import JobReaper
from adaptive_rag.jobs.service import EnqueueJobRequest, JobService

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


class ReapPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str


def _run(_context, payload: ReapPayload) -> dict[str, str]:
    return {"value": payload.value}


def _registry(*, max_retries: int = 2) -> JobRegistry:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="reap_echo",
            version=1,
            payload_model=ReapPayload,
            handler=_run,
            queue_name="default",
            allowed_scopes=frozenset({"system"}),
            retry_policy=RetryPolicy(max_retries=max_retries),
            lease_seconds=60,
        )
    )
    return registry


def _expired_claim(factory: sessionmaker[Session], registry: JobRegistry) -> tuple:
    with factory() as session:
        job = (
            JobService(session=session, registry=registry)
            .enqueue(
                EnqueueJobRequest.system(
                    job_type="reap_echo",
                    payload={"value": "x"},
                    run_after=NOW,
                )
            )
            .job
        )
        session.commit()
        job_id = job.id
    with factory() as session:
        claim = JobDispatcher(
            session=session,
            registry=registry,
            queue_names=("default",),
        ).claim_next(worker_id=uuid4(), now=NOW)
        assert claim is not None
        session.commit()
        return job_id, claim.attempt_id


def test_two_reapers_expire_one_attempt_once(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = _registry(max_retries=2)
    job_id, attempt_id = _expired_claim(job_session_factory, registry)
    ready = Barrier(2)

    def reap(_index: int) -> int:
        ready.wait(timeout=20)
        with job_session_factory() as session:
            count = JobReaper(session=session, registry=registry).run_once(
                now=NOW + timedelta(seconds=61),
                batch_size=100,
            )
            session.commit()
            return count

    with ThreadPoolExecutor(max_workers=2) as executor:
        counts = list(executor.map(reap, range(2)))

    with job_session_factory() as session:
        job = session.get(Job, job_id)
        attempt = session.get(JobAttempt, attempt_id)
        expired_events = session.scalar(
            select(func.count(JobEvent.id)).where(
                JobEvent.job_id == job_id,
                JobEvent.event_type == "expired",
            )
        )
        assert job is not None
        assert attempt is not None
        assert job.status == "queued"
        assert job.retry_count == 1
        assert attempt.status == "expired"
        assert expired_events == 1

    assert sum(counts) == 1


def test_expired_attempt_dead_letters_after_retry_budget(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = _registry(max_retries=0)
    job_id, _attempt_id = _expired_claim(job_session_factory, registry)

    with job_session_factory() as session:
        count = JobReaper(session=session, registry=registry).run_once(
            now=NOW + timedelta(seconds=61)
        )
        session.commit()

    with job_session_factory() as session:
        job = session.get(Job, job_id)
        assert job is not None
        assert job.status == "dead_letter"
        assert job.retry_count == 1
    assert count == 1


def test_unsupported_expired_attempt_does_not_poison_later_reaping(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = _registry(max_retries=2)
    first_job_id, _first_attempt_id = _expired_claim(job_session_factory, registry)
    second_job_id, _second_attempt_id = _expired_claim(job_session_factory, registry)
    with job_session_factory() as session:
        first = session.get(Job, first_job_id)
        assert first is not None
        first.job_type = "removed_handler"
        session.commit()

    with job_session_factory() as session:
        count = JobReaper(
            session=session,
            registry=registry,
            random_source=lambda: 0.0,
        ).run_once(now=NOW + timedelta(seconds=61))
        session.commit()

    with job_session_factory() as session:
        first = session.get(Job, first_job_id)
        second = session.get(Job, second_job_id)
        assert first is not None
        assert second is not None
        assert count == 2
        assert first.status == "blocked"
        assert first.last_error_code == "unsupported_handler_version"
        assert second.status == "queued"
