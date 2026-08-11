"""PostgreSQL claim concurrency, visibility, fairness, capacity, and fencing."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.db.models import Job, JobAttempt, JobQueue, Workspace
from adaptive_rag.db.repositories.job_runtime import JobRuntimeRepository
from adaptive_rag.jobs import ConcurrencyPolicy, JobHandlerDefinition, JobRegistry
from adaptive_rag.jobs.dispatcher import ClaimedJob, JobDispatcher
from adaptive_rag.jobs.service import EnqueueJobRequest, JobService

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


class EchoPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


def _echo(_context, payload: EchoPayload) -> dict[str, str]:
    return {"echo": payload.message}


def _registry(
    *,
    name: str = "echo",
    concurrency: ConcurrencyPolicy | None = None,
) -> JobRegistry:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name=name,
            version=1,
            payload_model=EchoPayload,
            handler=_echo,
            queue_name="default",
            allowed_scopes=frozenset({"workspace", "system"}),
            lease_seconds=60,
            concurrency=concurrency or ConcurrencyPolicy(),
        )
    )
    return registry


def _enqueue_ready_job(
    factory: sessionmaker[Session],
    registry: JobRegistry,
    *,
    job_type: str = "echo",
    queue_name: str | None = None,
    workspace_id: UUID | None = None,
    concurrency_key: str | None = None,
) -> UUID:
    with factory() as session:
        request = (
            EnqueueJobRequest.system(
                job_type=job_type,
                payload={"message": "ready"},
                run_after=NOW,
                queue_name=queue_name,
                concurrency_key=concurrency_key,
            )
            if workspace_id is None
            else EnqueueJobRequest.workspace(
                workspace_id=workspace_id,
                job_type=job_type,
                payload={"message": "ready"},
                run_after=NOW,
                queue_name=queue_name,
                concurrency_key=concurrency_key,
            )
        )
        result = JobService(session=session, registry=registry).enqueue(request)
        session.commit()
        return result.job.id


def _claim_and_commit(
    factory: sessionmaker[Session],
    registry: JobRegistry,
    *,
    worker_id: UUID,
) -> ClaimedJob | None:
    with factory() as session:
        claim = JobDispatcher(
            session=session,
            registry=registry,
            queue_names=("default",),
        ).claim_next(worker_id=worker_id, now=NOW)
        session.commit()
        return claim


def test_two_workers_create_one_attempt_for_one_job(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = _registry()
    job_id = _enqueue_ready_job(job_session_factory, registry)
    ready = Barrier(2)

    def claim(_index: int) -> ClaimedJob | None:
        ready.wait(timeout=20)
        return _claim_and_commit(
            job_session_factory,
            registry,
            worker_id=uuid4(),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        claims = list(executor.map(claim, range(2)))

    claimed_ids = [claim.job_id for claim in claims if claim is not None]
    with job_session_factory() as session:
        attempts = session.scalar(
            select(func.count(JobAttempt.id)).where(JobAttempt.job_id == job_id)
        )

    assert claimed_ids == [job_id]
    assert attempts == 1


def test_claim_is_committed_before_handler_work(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = _registry()
    job_id = _enqueue_ready_job(job_session_factory, registry)

    claim = _claim_and_commit(job_session_factory, registry, worker_id=uuid4())

    assert claim is not None
    with job_session_factory() as observer:
        observed = observer.get(Job, job_id)
        assert observed is not None
        assert observed.status == "running"
        assert observed.current_attempt_id == claim.attempt_id


def test_queue_default_lease_applies_to_handlers_using_platform_default(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="default_lease_echo",
            version=1,
            payload_model=EchoPayload,
            handler=_echo,
            queue_name="default",
            allowed_scopes=frozenset({"system"}),
        )
    )
    with job_session_factory() as session:
        queue = session.get(JobQueue, "default")
        assert queue is not None
        queue.default_lease_seconds = 90
        session.commit()
    _enqueue_ready_job(
        job_session_factory,
        registry,
        job_type="default_lease_echo",
    )

    claim = _claim_and_commit(job_session_factory, registry, worker_id=uuid4())

    assert claim is not None
    assert claim.lease_seconds == 90
    assert claim.lease_expires_at == NOW + timedelta(seconds=90)


def test_explicit_300_second_handler_lease_does_not_inherit_queue_default(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="explicit_lease_echo",
            version=1,
            payload_model=EchoPayload,
            handler=_echo,
            queue_name="default",
            allowed_scopes=frozenset({"system"}),
            lease_seconds=300,
        )
    )
    with job_session_factory() as session:
        queue = session.get(JobQueue, "default")
        assert queue is not None
        queue.default_lease_seconds = 15
        session.commit()
    _enqueue_ready_job(
        job_session_factory,
        registry,
        job_type="explicit_lease_echo",
    )

    claim = _claim_and_commit(job_session_factory, registry, worker_id=uuid4())

    assert claim is not None
    assert claim.lease_seconds == 300
    assert claim.lease_expires_at == NOW + timedelta(seconds=300)


def test_claims_round_robin_across_scopes(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = _registry(name="fair_echo")
    with job_session_factory() as session:
        first_workspace = Workspace(name="fair-a")
        second_workspace = Workspace(name="fair-b")
        session.add_all([first_workspace, second_workspace])
        session.commit()
        first_id = first_workspace.id
        second_id = second_workspace.id
    for _index in range(5):
        _enqueue_ready_job(
            job_session_factory,
            registry,
            job_type="fair_echo",
            workspace_id=first_id,
        )
    for _index in range(2):
        _enqueue_ready_job(
            job_session_factory,
            registry,
            job_type="fair_echo",
            workspace_id=second_id,
        )

    claims = [
        _claim_and_commit(job_session_factory, registry, worker_id=uuid4())
        for _index in range(4)
    ]

    assert [claim.workspace_id for claim in claims if claim is not None] == [
        first_id,
        second_id,
        first_id,
        second_id,
    ]


def test_busy_first_queue_does_not_starve_second_queue(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = _registry(name="rotating_echo")
    for _index in range(5):
        _enqueue_ready_job(
            job_session_factory,
            registry,
            job_type="rotating_echo",
            queue_name="ingestion",
        )
    _enqueue_ready_job(
        job_session_factory,
        registry,
        job_type="rotating_echo",
        queue_name="system",
    )

    with job_session_factory() as session:
        dispatcher = JobDispatcher(
            session=session,
            registry=registry,
            queue_names=("ingestion", "system"),
        )
        first = dispatcher.claim_next(worker_id=uuid4(), now=NOW)
        session.commit()
        second = dispatcher.claim_next(worker_id=uuid4(), now=NOW)
        session.commit()

    assert first is not None
    assert second is not None
    assert [first.queue_name, second.queue_name] == ["ingestion", "system"]


@pytest.mark.parametrize("limit_kind", ["queue", "workspace", "handler", "key"])
def test_claim_respects_capacity_under_race(
    limit_kind: str,
    job_session_factory: sessionmaker[Session],
) -> None:
    concurrency = ConcurrencyPolicy(
        handler_limit=2 if limit_kind == "handler" else None,
        key_limit=2 if limit_kind == "key" else None,
    )
    job_type = f"capacity_{limit_kind}"
    registry = _registry(name=job_type, concurrency=concurrency)
    workspace_id = None
    with job_session_factory() as session:
        queue = session.get(JobQueue, "default")
        assert queue is not None
        if limit_kind == "queue":
            queue.global_concurrency_limit = 2
        elif limit_kind == "workspace":
            queue.workspace_concurrency_limit = 2
            workspace = Workspace(name="capacity-workspace")
            session.add(workspace)
            session.flush()
            workspace_id = workspace.id
        session.commit()
    for _index in range(8):
        _enqueue_ready_job(
            job_session_factory,
            registry,
            job_type=job_type,
            workspace_id=workspace_id,
            concurrency_key="shared" if limit_kind == "key" else None,
        )
    ready = Barrier(8)

    def claim(_index: int) -> ClaimedJob | None:
        ready.wait(timeout=20)
        return _claim_and_commit(
            job_session_factory,
            registry,
            worker_id=uuid4(),
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        claims = list(executor.map(claim, range(8)))

    assert len([claim for claim in claims if claim is not None]) == 2


@pytest.mark.parametrize("limit_kind", ["handler", "key"])
def test_shared_capacity_holds_across_two_queues(
    limit_kind: str,
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = _registry(
        name=f"shared_{limit_kind}",
        concurrency=ConcurrencyPolicy(
            handler_limit=1 if limit_kind == "handler" else None,
            key_limit=1 if limit_kind == "key" else None,
        ),
    )
    for queue_name in ("ingestion", "system"):
        _enqueue_ready_job(
            job_session_factory,
            registry,
            job_type=f"shared_{limit_kind}",
            queue_name=queue_name,
            concurrency_key="shared" if limit_kind == "key" else None,
        )
    ready = Barrier(2)

    def claim(queue_name: str) -> ClaimedJob | None:
        ready.wait(timeout=20)
        with job_session_factory() as session:
            result = JobDispatcher(
                session=session,
                registry=registry,
                queue_names=(queue_name,),
            ).claim_next(worker_id=uuid4(), now=NOW)
            session.commit()
            return result

    with ThreadPoolExecutor(max_workers=2) as executor:
        claims = list(executor.map(claim, ("ingestion", "system")))

    assert len([claim for claim in claims if claim is not None]) == 1


def test_obsolete_attempt_cannot_heartbeat_or_complete(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = _registry(name="fenced_echo")
    _enqueue_ready_job(
        job_session_factory,
        registry,
        job_type="fenced_echo",
    )
    first = _claim_and_commit(job_session_factory, registry, worker_id=uuid4())
    assert first is not None
    with job_session_factory() as session:
        job = session.get(Job, first.job_id)
        attempt = session.get(JobAttempt, first.attempt_id)
        assert job is not None
        assert attempt is not None
        job.status = "queued"
        job.current_attempt_id = None
        job.locked_by = None
        job.locked_until = None
        attempt.status = "expired"
        attempt.finished_at = NOW
        session.commit()
    second = _claim_and_commit(job_session_factory, registry, worker_id=uuid4())
    assert second is not None

    with job_session_factory() as session:
        runtime = JobRuntimeRepository(session)
        assert (
            runtime.heartbeat(
                job_id=first.job_id,
                attempt_id=first.attempt_id,
                now=NOW,
                lease_expires_at=first.lease_expires_at,
            )
            is False
        )
        assert (
            runtime.finish_fenced(
                job_id=first.job_id,
                attempt_id=first.attempt_id,
                now=NOW,
                job_status="succeeded",
                attempt_status="succeeded",
                result_json={},
            )
            is False
        )
        assert (
            runtime.heartbeat(
                job_id=second.job_id,
                attempt_id=second.attempt_id,
                now=NOW,
                lease_expires_at=second.lease_expires_at,
            )
            is True
        )
        session.commit()
