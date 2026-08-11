"""General worker transaction boundaries on PostgreSQL."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.db.models import Job
from adaptive_rag.db.models import JobWorker as JobWorkerPresence
from adaptive_rag.db.repositories import SourceRepository, WorkspaceRepository
from adaptive_rag.ingestion_ops import enqueue_source_ingestion
from adaptive_rag.jobs import JobContext, JobHandlerDefinition, JobRegistry
from adaptive_rag.jobs.handlers import build_ingestion_registry
from adaptive_rag.jobs.service import EnqueueJobRequest, JobService
from adaptive_rag.jobs.worker import JobWorker, PostgresNotificationWaiter

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


class BlockingPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str


def test_worker_commits_claim_before_invoking_handler(
    job_session_factory: sessionmaker[Session],
) -> None:
    async def scenario() -> None:
        entered = asyncio.Event()
        release = asyncio.Event()

        async def handler(
            _context: JobContext,
            payload: BlockingPayload,
        ) -> dict[str, str]:
            entered.set()
            await release.wait()
            return {"value": payload.value}

        registry = JobRegistry()
        registry.register(
            JobHandlerDefinition(
                name="blocking_worker",
                version=1,
                payload_model=BlockingPayload,
                handler=handler,
                queue_name="default",
                allowed_scopes=frozenset({"system"}),
                lease_seconds=60,
            )
        )
        with job_session_factory() as session:
            job = (
                JobService(session=session, registry=registry)
                .enqueue(
                    EnqueueJobRequest.system(
                        job_type="blocking_worker",
                        payload={"value": "done"},
                        run_after=NOW,
                    )
                )
                .job
            )
            session.commit()
            job_id = job.id

        worker = JobWorker(
            session_factory=job_session_factory,
            registry=registry,
            queue_names=("default",),
            now_source=lambda: NOW,
            heartbeat_interval_seconds=30,
        )
        task = asyncio.create_task(worker.run_once())
        await asyncio.wait_for(entered.wait(), timeout=10)
        with job_session_factory() as observer:
            observed = observer.get(Job, job_id)
            assert observed is not None
            assert observed.status == "running"
            assert observed.current_attempt_id is not None
        release.set()
        report = await asyncio.wait_for(task, timeout=10)

        assert report.status == "succeeded"
        with job_session_factory() as observer:
            assert observer.get(Job, job_id).status == "succeeded"

    asyncio.run(scenario())


def test_general_worker_runs_ingestion_handler_and_enqueues_indexing(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = build_ingestion_registry(session_factory=job_session_factory)
    with job_session_factory() as session:
        workspace = WorkspaceRepository(session).create(name="worker-ingestion")
        source = SourceRepository(session).create(
            workspace_id=workspace.id,
            source_type="markdown",
            external_id="worker.md",
            extra_metadata={"content": "# Worker ingestion"},
        )
        ingest_job = (
            JobService(session=session, registry=registry)
            .enqueue(
                EnqueueJobRequest.workspace(
                    workspace_id=workspace.id,
                    job_type="ingest_source",
                    payload={"source_id": str(source.id)},
                    idempotency_key=f"source:{source.id}",
                    run_after=NOW,
                )
            )
            .job
        )
        session.commit()
        ingest_job_id = ingest_job.id

    report = JobWorker(
        session_factory=job_session_factory,
        registry=registry,
        queue_names=("ingestion",),
        now_source=lambda: NOW,
    ).run_once_sync()

    assert report.status == "succeeded"
    with job_session_factory() as session:
        ingest_job = session.get(Job, ingest_job_id)
        indexing_job = (
            session.query(Job).filter(Job.job_type == "index_document_version").one()
        )
        assert ingest_job is not None
        assert ingest_job.status == "succeeded"
        assert indexing_job.status == "queued"


def test_ingestion_enqueue_uses_platform_idempotency_on_postgresql(
    job_session_factory: sessionmaker[Session],
) -> None:
    with job_session_factory() as session:
        workspace = WorkspaceRepository(session).create(name="platform-enqueue")
        source = SourceRepository(session).create(
            workspace_id=workspace.id,
            source_type="markdown",
            external_id="platform.md",
            extra_metadata={"content": "# Platform enqueue"},
        )
        session.flush()

        first = enqueue_source_ingestion(
            session,
            workspace_id=workspace.id,
            source_id=source.id,
        )
        second = enqueue_source_ingestion(
            session,
            workspace_id=workspace.id,
            source_id=source.id,
        )
        session.commit()

        assert first.id == second.id
        assert first.queue_name == "ingestion"
        assert first.idempotency_key == f"source:{source.id}"


def test_worker_workspace_filter_does_not_claim_other_workspaces(
    job_session_factory: sessionmaker[Session],
) -> None:
    async def handler(
        _context: JobContext,
        payload: BlockingPayload,
    ) -> dict[str, str]:
        return {"value": payload.value}

    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="workspace_worker",
            version=1,
            payload_model=BlockingPayload,
            handler=handler,
            queue_name="default",
            allowed_scopes=frozenset({"workspace"}),
        )
    )
    with job_session_factory() as session:
        first = WorkspaceRepository(session).create(name="worker-filter-first")
        second = WorkspaceRepository(session).create(name="worker-filter-second")
        first_job = (
            JobService(session=session, registry=registry)
            .enqueue(
                EnqueueJobRequest.workspace(
                    workspace_id=first.id,
                    job_type="workspace_worker",
                    payload={"value": "first"},
                    run_after=NOW,
                )
            )
            .job
        )
        second_job = (
            JobService(session=session, registry=registry)
            .enqueue(
                EnqueueJobRequest.workspace(
                    workspace_id=second.id,
                    job_type="workspace_worker",
                    payload={"value": "second"},
                    run_after=NOW,
                )
            )
            .job
        )
        session.commit()
        first_id = first.id
        first_job_id = first_job.id
        second_job_id = second_job.id

    report = JobWorker(
        session_factory=job_session_factory,
        registry=registry,
        queue_names=("default",),
        workspace_id=first_id,
        now_source=lambda: NOW,
    ).run_once_sync()

    assert report.job_id == first_job_id
    with job_session_factory() as session:
        assert session.get(Job, first_job_id).status == "succeeded"
        assert session.get(Job, second_job_id).status == "queued"


def test_worker_refuses_completion_after_heartbeat_loses_fence(
    job_session_factory: sessionmaker[Session],
) -> None:
    async def scenario() -> None:
        release = asyncio.Event()

        async def handler(
            _context: JobContext,
            payload: BlockingPayload,
        ) -> dict[str, str]:
            await release.wait()
            return {"value": payload.value}

        registry = JobRegistry()
        registry.register(
            JobHandlerDefinition(
                name="fenced_worker",
                version=1,
                payload_model=BlockingPayload,
                handler=handler,
                queue_name="default",
                allowed_scopes=frozenset({"system"}),
                lease_seconds=60,
            )
        )
        with job_session_factory() as session:
            job = (
                JobService(session=session, registry=registry)
                .enqueue(
                    EnqueueJobRequest.system(
                        job_type="fenced_worker",
                        payload={"value": "never-finalized"},
                        run_after=NOW,
                    )
                )
                .job
            )
            session.commit()
            job_id = job.id
        worker = JobWorker(
            session_factory=job_session_factory,
            registry=registry,
            queue_names=("default",),
            now_source=lambda: NOW,
            heartbeat_interval_seconds=0.01,
        )
        worker._heartbeat_once = lambda _claim: False  # type: ignore[method-assign]

        report = await asyncio.wait_for(worker.run_once(), timeout=10)

        assert report.status == "fenced"
        with job_session_factory() as observer:
            assert observer.get(Job, job_id).status == "running"
        release.set()

    asyncio.run(scenario())


def test_worker_presence_progresses_live_draining_shutdown(
    job_session_factory: sessionmaker[Session],
) -> None:
    async def scenario() -> None:
        registry = JobRegistry()
        worker = JobWorker(
            session_factory=job_session_factory,
            registry=registry,
            queue_names=("default",),
            now_source=lambda: NOW,
            heartbeat_interval_seconds=30,
        )
        task = asyncio.create_task(worker.run(poll_interval_seconds=0.01))
        for _index in range(100):
            with job_session_factory() as observer:
                if observer.get(JobWorkerPresence, worker.worker_id) is not None:
                    break
            await asyncio.sleep(0.01)
        else:
            raise AssertionError("worker presence was not registered")

        worker.request_shutdown()
        await asyncio.wait_for(task, timeout=10)

        with job_session_factory() as observer:
            presence = observer.get(JobWorkerPresence, worker.worker_id)
            assert presence is not None
            assert presence.draining_at is not None
            assert presence.shutdown_at is not None

    asyncio.run(scenario())


def test_postgresql_notification_is_commit_aware(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="notify_worker",
            version=1,
            payload_model=BlockingPayload,
            handler=lambda _context, payload: {"value": payload.value},
            queue_name="default",
            allowed_scopes=frozenset({"system"}),
        )
    )
    waiter = PostgresNotificationWaiter.from_session_factory(job_session_factory)
    waiter.open()
    try:
        with job_session_factory() as session:
            JobService(session=session, registry=registry).enqueue(
                EnqueueJobRequest.system(
                    job_type="notify_worker",
                    payload={"value": "rolled-back"},
                    run_after=NOW,
                )
            )
            session.rollback()
        assert waiter.wait(timeout_seconds=0.2) is False

        with job_session_factory() as session:
            JobService(session=session, registry=registry).enqueue(
                EnqueueJobRequest.system(
                    job_type="notify_worker",
                    payload={"value": "committed"},
                    run_after=NOW,
                )
            )
            session.commit()
        assert waiter.wait(timeout_seconds=2) is True
    finally:
        waiter.close()
