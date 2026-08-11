"""Transactional enqueue behavior that depends on real PostgreSQL semantics."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.db.models import Job, Workspace
from adaptive_rag.db.repositories.jobs import JobRepository
from adaptive_rag.jobs import JobHandlerDefinition, JobRegistry
from adaptive_rag.jobs.service import EnqueueJobRequest, JobService


class EchoPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


def _echo(_context, payload: EchoPayload) -> dict[str, str]:
    return {"echo": payload.message}


def _registry() -> JobRegistry:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="echo",
            version=1,
            payload_model=EchoPayload,
            handler=_echo,
            queue_name="default",
            allowed_scopes=frozenset({"workspace", "system"}),
        )
    )
    return registry


def test_rolled_back_enqueue_is_not_visible(
    job_session_factory: sessionmaker[Session],
) -> None:
    idempotency_key = f"rollback-{uuid4()}"
    with job_session_factory() as session:
        result = JobService(session=session, registry=_registry()).enqueue(
            EnqueueJobRequest.system(
                job_type="echo",
                payload={"message": "rollback"},
                idempotency_key=idempotency_key,
            )
        )
        job_id = result.job.id
        session.rollback()

    with job_session_factory() as verification_session:
        assert verification_session.get(Job, job_id) is None


def test_concurrent_idempotent_enqueue_preserves_outer_business_writes(
    job_session_factory: sessionmaker[Session],
) -> None:
    workers = 8
    ready = Barrier(workers)
    idempotency_key = f"race-{uuid4()}"
    fingerprint = "a" * 64
    run_after = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)

    def enqueue(index: int) -> tuple[UUID, bool]:
        with job_session_factory() as session:
            workspace = Workspace(name=f"race-business-write-{idempotency_key}-{index}")
            session.add(workspace)
            session.flush()
            repository = JobRepository(session)
            assert (
                repository.find_open_idempotent(
                    scope="system",
                    workspace_id=None,
                    job_type="echo",
                    handler_version=1,
                    idempotency_key=idempotency_key,
                )
                is None
            )
            ready.wait(timeout=20)
            job, created = repository.enqueue_validated(
                scope="system",
                workspace_id=None,
                queue_name="default",
                job_type="echo",
                handler_version=1,
                payload_json={"message": "same"},
                priority=0,
                max_retries=3,
                run_after=run_after,
                idempotency_key=idempotency_key,
                idempotency_fingerprint=fingerprint,
                schedule_id=None,
                scheduled_for=None,
                concurrency_key=None,
            )
            session.commit()
            return job.id, created

    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(enqueue, range(workers)))

    job_ids = {job_id for job_id, _created in results}
    with job_session_factory() as verification_session:
        job_count = verification_session.scalar(
            select(func.count(Job.id)).where(
                Job.scope == "system",
                Job.idempotency_key == idempotency_key,
            )
        )
        workspace_count = verification_session.scalar(
            select(func.count(Workspace.id)).where(
                Workspace.name.like(f"race-business-write-{idempotency_key}-%")
            )
        )

    assert len(job_ids) == 1
    assert sum(created for _job_id, created in results) == 1
    assert job_count == 1
    assert workspace_count == workers
