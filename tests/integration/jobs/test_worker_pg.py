"""General worker transaction boundaries on PostgreSQL."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier, Event, Lock, get_ident
from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.db.models import Job, JobAttempt, JobEvent
from adaptive_rag.db.models import JobWorker as JobWorkerPresence
from adaptive_rag.db.repositories import SourceRepository, WorkspaceRepository
from adaptive_rag.db.repositories.job_runtime import JobRuntimeRepository
from adaptive_rag.ingestion_ops import enqueue_source_ingestion, run_next_ingestion_job
from adaptive_rag.jobs import (
    BlockedJobError,
    JobContext,
    JobHandlerDefinition,
    JobRegistry,
    RetryPolicy,
)
from adaptive_rag.jobs.dispatcher import JobDispatcher
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


def test_legacy_one_second_lease_maps_to_the_internal_minimum(
    job_session_factory: sessionmaker[Session],
) -> None:
    with job_session_factory() as session:
        workspace = WorkspaceRepository(session).create(name="legacy-short-lease")
        source = SourceRepository(session).create(
            workspace_id=workspace.id,
            source_type="markdown",
            external_id="legacy-short-lease.md",
            extra_metadata={"content": "# Short lease"},
        )
        job = enqueue_source_ingestion(
            session,
            workspace_id=workspace.id,
            source_id=source.id,
        )
        job.run_after = NOW
        session.commit()
        workspace_id = workspace.id
        job_id = job.id

    with job_session_factory() as session:
        report = run_next_ingestion_job(
            session,
            workspace_id=workspace_id,
            worker_id="legacy-one-second",
            lease_seconds=1,
            now=NOW,
        )

    with job_session_factory() as session:
        attempt = session.scalar(select(JobAttempt).where(JobAttempt.job_id == job_id))
        assert attempt is not None
        assert attempt.lease_expires_at - attempt.started_at == timedelta(seconds=15)
        assert report.status == "processed"


def test_legacy_runner_commits_enqueued_job_before_general_worker(
    job_database_url: str,
) -> None:
    engine = create_engine(
        job_database_url,
        pool_pre_ping=True,
        connect_args={"options": "-c lock_timeout=1000"},
    )
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        with session_factory() as session:
            workspace = WorkspaceRepository(session).create(
                name="legacy-uncommitted-enqueue"
            )
            source = SourceRepository(session).create(
                workspace_id=workspace.id,
                source_type="markdown",
                external_id="legacy-uncommitted-enqueue.md",
                extra_metadata={"content": "# Transaction boundary"},
            )
            job = enqueue_source_ingestion(
                session,
                workspace_id=workspace.id,
                source_id=source.id,
                run_after=NOW,
            )
            job_id = job.id

            report = run_next_ingestion_job(
                session,
                workspace_id=workspace.id,
                worker_id="legacy-uncommitted-enqueue",
                now=NOW,
            )

        assert report.status == "processed"
        assert report.job_id == job_id
        with session_factory() as session:
            persisted_job = session.get(Job, job_id)
            assert persisted_job is not None
            assert persisted_job.status == "succeeded"
    finally:
        engine.dispose()


def test_legacy_runner_refreshes_caller_state_after_general_worker(
    job_session_factory: sessionmaker[Session],
) -> None:
    with job_session_factory() as session:
        workspace = WorkspaceRepository(session).create(
            name="legacy-worker-state-refresh"
        )
        source = SourceRepository(session).create(
            workspace_id=workspace.id,
            source_type="markdown",
            external_id="legacy-worker-state-refresh.md",
            extra_metadata={"content": "# Worker state refresh"},
        )
        job = enqueue_source_ingestion(
            session,
            workspace_id=workspace.id,
            source_id=source.id,
            run_after=NOW,
        )
        session.commit()
        assert job.status == "queued"

        report = run_next_ingestion_job(
            session,
            workspace_id=workspace.id,
            worker_id="legacy-worker-state-refresh",
            now=NOW,
        )

        assert report.status == "processed"
        assert session.get(Job, job.id) is job
        assert job.status == "succeeded"


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


@pytest.mark.parametrize("heartbeat_failure", ["lost_fence", "database_error"])
def test_worker_refuses_completion_after_heartbeat_loses_fence(
    heartbeat_failure: str,
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
        if heartbeat_failure == "database_error":
            def fail_heartbeat(_claim):  # type: ignore[no-untyped-def]
                raise SQLAlchemyError("database unavailable")

            worker._heartbeat_once = fail_heartbeat  # type: ignore[method-assign]
        else:
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


def test_worker_presence_heartbeats_while_a_handler_is_running(
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
                name="presence_heartbeat_worker",
                version=1,
                payload_model=BlockingPayload,
                handler=handler,
                queue_name="default",
                allowed_scopes=frozenset({"system"}),
                lease_seconds=60,
            )
        )
        with job_session_factory() as session:
            JobService(session=session, registry=registry).enqueue(
                EnqueueJobRequest.system(
                    job_type="presence_heartbeat_worker",
                    payload={"value": "done"},
                )
            )
            session.commit()

        worker = JobWorker(
            session_factory=job_session_factory,
            registry=registry,
            queue_names=("default",),
            presence_heartbeat_interval_seconds=0.01,
        )
        task = asyncio.create_task(worker.run(poll_interval_seconds=0.01))
        await asyncio.wait_for(entered.wait(), timeout=10)
        with job_session_factory() as observer:
            initial = observer.get(JobWorkerPresence, worker.worker_id)
            assert initial is not None
            initial_heartbeat = initial.heartbeat_at

        for _index in range(500):
            with job_session_factory() as observer:
                heartbeat = observer.scalar(
                    select(JobWorkerPresence.heartbeat_at).where(
                        JobWorkerPresence.id == worker.worker_id
                    )
                )
            if heartbeat is not None and heartbeat > initial_heartbeat:
                break
            await asyncio.sleep(0.01)
        else:
            raise AssertionError("worker presence did not heartbeat during the handler")

        release.set()
        worker.request_shutdown()
        await asyncio.wait_for(task, timeout=10)

    asyncio.run(scenario())


def test_worker_supervisor_contains_presence_database_failures(
    job_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = JobRegistry()
    worker = JobWorker(
        session_factory=job_session_factory,
        registry=registry,
        queue_names=("default",),
        presence_heartbeat_interval_seconds=0.01,
        presence_retry_delay_seconds=0,
    )

    def unavailable() -> None:
        raise SQLAlchemyError("presence database unavailable")

    monkeypatch.setattr(worker, "_register_presence", unavailable)
    monkeypatch.setattr(worker, "_heartbeat_presence", unavailable)
    monkeypatch.setattr(worker, "_mark_presence_draining", unavailable)
    monkeypatch.setattr(worker, "_mark_presence_shutdown", unavailable)

    async def scenario() -> None:
        task = asyncio.create_task(worker.run(poll_interval_seconds=0.01))
        await asyncio.sleep(0.05)
        worker.request_shutdown()
        await asyncio.wait_for(task, timeout=2)

    asyncio.run(scenario())


def test_worker_registers_presence_after_initial_database_failure(
    job_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = JobWorker(
        session_factory=job_session_factory,
        registry=JobRegistry(),
        queue_names=("default",),
        presence_heartbeat_interval_seconds=0.01,
        presence_retry_delay_seconds=0,
    )
    original_register = worker._register_presence
    attempts = 0

    def initially_unavailable() -> None:
        nonlocal attempts
        attempts += 1
        if attempts <= 3:
            raise SQLAlchemyError("database unavailable during startup")
        original_register()

    monkeypatch.setattr(worker, "_register_presence", initially_unavailable)

    async def scenario() -> None:
        task = asyncio.create_task(worker.run(poll_interval_seconds=0.01))
        for _index in range(200):
            with job_session_factory() as observer:
                presence = observer.get(JobWorkerPresence, worker.worker_id)
            if presence is not None:
                break
            await asyncio.sleep(0.01)
        else:
            raise AssertionError("worker did not register after database recovery")
        worker.request_shutdown()
        await asyncio.wait_for(task, timeout=2)

    asyncio.run(scenario())
    assert attempts >= 4


def test_sigterm_bounds_drain_for_a_blocked_synchronous_handler(
    job_database_url: str,
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="blocking_sync_shutdown",
            version=1,
            payload_model=BlockingPayload,
            handler=lambda _context, payload: {"value": payload.value},
            queue_name="default",
            allowed_scopes=frozenset({"system"}),
            lease_seconds=15,
        )
    )
    with job_session_factory() as session:
        job = JobService(session=session, registry=registry).enqueue(
            EnqueueJobRequest.system(
                job_type="blocking_sync_shutdown",
                payload={"value": "never-finished"},
                run_after=datetime.now(UTC),
            )
        ).job
        session.commit()
        job_id = job.id

    helper = Path(__file__).with_name("_blocking_sync_worker_process.py")
    process = subprocess.Popen(
        [sys.executable, str(helper), job_database_url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        for _index in range(200):
            with job_session_factory() as observer:
                status = observer.scalar(select(Job.status).where(Job.id == job_id))
            if status == "running":
                break
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise AssertionError(
                    f"worker exited before claim\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
                )
            time.sleep(0.05)
        else:
            raise AssertionError("synchronous handler did not start")

        started = time.monotonic()
        process.terminate()
        return_code = process.wait(timeout=5)
        elapsed = time.monotonic() - started

        assert return_code == 0
        assert elapsed < 3
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_detached_sync_handler_is_fenced_and_retains_local_capacity(
    job_session_factory: sessionmaker[Session],
) -> None:
    entered = Event()
    observed_fence = Event()
    release = Event()

    def handler(context: JobContext, payload: BlockingPayload) -> object:
        if payload.value == "first":
            entered.set()
            for _index in range(500):
                if not context.is_lease_healthy():
                    observed_fence.set()
                    break
                time.sleep(0.01)
            release.wait(timeout=10)
        return {"value": payload.value}

    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="detached_capacity",
            version=1,
            payload_model=BlockingPayload,
            handler=handler,
            queue_name="default",
            allowed_scopes=frozenset({"system"}),
            lease_seconds=15,
        )
    )
    with job_session_factory() as session:
        first = JobService(session=session, registry=registry).enqueue(
            EnqueueJobRequest.system(
                job_type="detached_capacity",
                payload={"value": "first"},
                run_after=datetime.now(UTC) - timedelta(seconds=1),
            )
        ).job
        second = JobService(session=session, registry=registry).enqueue(
            EnqueueJobRequest.system(
                job_type="detached_capacity",
                payload={"value": "second"},
                run_after=datetime.now(UTC),
            )
        ).job
        session.commit()
        first_id = first.id
        second_id = second.id

    worker = JobWorker(
        session_factory=job_session_factory,
        registry=registry,
        queue_names=("default",),
        max_concurrency=1,
    )

    async def scenario() -> None:
        task = asyncio.create_task(
            worker.run(poll_interval_seconds=0.01, drain_timeout_seconds=0.05)
        )
        started = await asyncio.to_thread(entered.wait, 5)
        assert started is True
        worker.request_shutdown()
        await asyncio.wait_for(task, timeout=2)

    asyncio.run(scenario())

    assert observed_fence.wait(timeout=2) is True
    capacity_report = worker.run_once_sync()
    assert capacity_report.status == "local_capacity"
    with job_session_factory() as session:
        assert session.get(Job, first_id).status == "running"
        assert session.get(Job, second_id).status == "queued"

    release.set()
    for _index in range(200):
        report = worker.run_once_sync()
        if report.status != "local_capacity":
            break
        time.sleep(0.01)
    else:
        raise AssertionError("detached handler did not release local capacity")
    assert report.status == "succeeded"
    assert report.job_id == second_id


def test_worker_rotates_queue_priority_across_committed_claims(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="worker_queue_rotation",
            version=1,
            payload_model=BlockingPayload,
            handler=lambda _context, payload: {"value": payload.value},
            queue_name="ingestion",
            allowed_scopes=frozenset({"system"}),
        )
    )
    with job_session_factory() as session:
        service = JobService(session=session, registry=registry)
        for index in range(3):
            service.enqueue(
                EnqueueJobRequest.system(
                    job_type="worker_queue_rotation",
                    payload={"value": f"ingestion-{index}"},
                    queue_name="ingestion",
                    run_after=NOW,
                )
            )
        service.enqueue(
            EnqueueJobRequest.system(
                job_type="worker_queue_rotation",
                payload={"value": "system"},
                queue_name="system",
                run_after=NOW,
            )
        )
        session.commit()

    worker = JobWorker(
        session_factory=job_session_factory,
        registry=registry,
        queue_names=("ingestion", "system"),
        now_source=lambda: NOW,
    )

    first = worker.run_once_sync()
    second = worker.run_once_sync()

    assert first.result == {"value": "ingestion-0"}
    assert second.result == {"value": "system"}


def test_concurrent_rotated_claims_do_not_deadlock_queue_rows(
    job_session_factory: sessionmaker[Session],
    monkeypatch,
) -> None:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="deadlock_probe",
            version=1,
            payload_model=BlockingPayload,
            handler=lambda _context, payload: {"value": payload.value},
            queue_name="ingestion",
            allowed_scopes=frozenset({"system"}),
        )
    )
    barrier = Barrier(2)
    guard = Lock()
    synchronized_threads: set[int] = set()
    original = JobRuntimeRepository.claim_from_queue

    def synchronized_first_queue(self, **kwargs):  # type: ignore[no-untyped-def]
        result = original(self, **kwargs)
        thread_id = get_ident()
        with guard:
            first_for_thread = thread_id not in synchronized_threads
            synchronized_threads.add(thread_id)
        if first_for_thread:
            barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(
        JobRuntimeRepository,
        "claim_from_queue",
        synchronized_first_queue,
    )
    worker = JobWorker(
        session_factory=job_session_factory,
        registry=registry,
        queue_names=("ingestion", "system"),
        max_concurrency=2,
        now_source=lambda: NOW,
    )

    reports = asyncio.run(asyncio.wait_for(worker._run_batch_once(), timeout=10))

    assert [report.status for report in reports] == ["idle", "idle"]


def test_secret_bearing_handler_error_is_safely_finalized(
    job_session_factory: sessionmaker[Session],
) -> None:
    def handler(_context: JobContext, _payload: BlockingPayload) -> object:
        raise RuntimeError("password=do-not-persist token=also-secret")

    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="secret_failure",
            version=1,
            payload_model=BlockingPayload,
            handler=handler,
            queue_name="default",
            allowed_scopes=frozenset({"system"}),
        )
    )
    with job_session_factory() as session:
        job = JobService(session=session, registry=registry).enqueue(
            EnqueueJobRequest.system(
                job_type="secret_failure",
                payload={"value": "fail"},
                run_after=NOW,
            )
        ).job
        session.commit()
        job_id = job.id

    report = JobWorker(
        session_factory=job_session_factory,
        registry=registry,
        queue_names=("default",),
        now_source=lambda: NOW,
    ).run_once_sync()

    with job_session_factory() as session:
        job = session.get(Job, job_id)
        attempt = session.scalar(select(JobAttempt).where(JobAttempt.job_id == job_id))
        events = list(
            session.scalars(select(JobEvent).where(JobEvent.job_id == job_id))
        )
        assert job is not None
        assert attempt is not None
        persisted = " ".join(
            message
            for message in (
                job.last_error_message,
                attempt.error_message,
                *(event.message for event in events),
            )
            if message is not None
        )
        assert "do-not-persist" not in persisted
        assert "also-secret" not in persisted
        assert job.last_trace_id is not None
        assert attempt.trace_id == job.last_trace_id
        assert report.status == "retry_scheduled"
        assert report.error_message == job.last_error_message


def test_worker_report_exposes_only_the_persisted_redacted_result(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="secret_result",
            version=1,
            payload_model=BlockingPayload,
            handler=lambda _context, _payload: {
                "api_key": "raw-secret",
                "value": "safe",
            },
            queue_name="default",
            allowed_scopes=frozenset({"system"}),
        )
    )
    with job_session_factory() as session:
        job = JobService(session=session, registry=registry).enqueue(
            EnqueueJobRequest.system(
                job_type="secret_result",
                payload={"value": "run"},
                run_after=NOW,
            )
        ).job
        session.commit()
        job_id = job.id

    report = JobWorker(
        session_factory=job_session_factory,
        registry=registry,
        queue_names=("default",),
        now_source=lambda: NOW,
    ).run_once_sync()

    with job_session_factory() as session:
        job = session.get(Job, job_id)
        assert job is not None
        assert job.result_json == {"api_key": "[REDACTED]", "value": "safe"}
        assert report.result == job.result_json


def test_expected_platform_error_diagnostic_is_not_persisted(
    job_session_factory: sessionmaker[Session],
) -> None:
    def handler(_context: JobContext, _payload: BlockingPayload) -> object:
        raise BlockedJobError("signed_url=https://example.test?token=raw-secret")

    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="unsafe_blocked_failure",
            version=1,
            payload_model=BlockingPayload,
            handler=handler,
            queue_name="default",
            allowed_scopes=frozenset({"system"}),
        )
    )
    with job_session_factory() as session:
        job = JobService(session=session, registry=registry).enqueue(
            EnqueueJobRequest.system(
                job_type="unsafe_blocked_failure",
                payload={"value": "fail"},
                run_after=NOW,
            )
        ).job
        session.commit()
        job_id = job.id

    report = JobWorker(
        session_factory=job_session_factory,
        registry=registry,
        queue_names=("default",),
        now_source=lambda: NOW,
    ).run_once_sync()

    with job_session_factory() as session:
        job = session.get(Job, job_id)
        attempt = session.scalar(select(JobAttempt).where(JobAttempt.job_id == job_id))
        events = list(
            session.scalars(select(JobEvent).where(JobEvent.job_id == job_id))
        )
        assert job is not None
        assert attempt is not None
        persisted = " ".join(
            value
            for value in (
                job.last_error_message,
                attempt.error_message,
                *(event.message for event in events),
            )
            if value is not None
        )
        assert "raw-secret" not in persisted
        assert "signed_url" not in persisted
        assert job.last_error_code == "job_blocked"
        assert report.status == "blocked"
        assert report.error_message == "job is blocked; see trace ID"


def test_oversized_result_does_not_escape_or_leave_the_job_running(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="oversized_result",
            version=1,
            payload_model=BlockingPayload,
            handler=lambda _context, _payload: {"value": "x" * (65 * 1024)},
            queue_name="default",
            allowed_scopes=frozenset({"system"}),
        )
    )
    with job_session_factory() as session:
        job = JobService(session=session, registry=registry).enqueue(
            EnqueueJobRequest.system(
                job_type="oversized_result",
                payload={"value": "fail"},
                run_after=NOW,
            )
        ).job
        session.commit()
        job_id = job.id

    report = JobWorker(
        session_factory=job_session_factory,
        registry=registry,
        queue_names=("default",),
        now_source=lambda: NOW,
    ).run_once_sync()

    with job_session_factory() as session:
        job = session.get(Job, job_id)
        assert job is not None
        assert job.status == "dead_letter"
        assert job.current_attempt_id is None
        assert job.last_error_code == "job_result_too_large"
        assert report.status == "dead_letter"


def test_daemon_worker_reaps_expired_attempt_before_claiming_again(
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="reaping_worker",
            version=1,
            payload_model=BlockingPayload,
            handler=lambda _context, payload: {"value": payload.value},
            queue_name="default",
            allowed_scopes=frozenset({"system"}),
            retry_policy=RetryPolicy(
                max_retries=2,
                base_delay_seconds=0.001,
                max_delay_seconds=0.001,
            ),
            lease_seconds=15,
        )
    )
    wall_now = datetime.now(UTC)
    with job_session_factory() as session:
        job = JobService(session=session, registry=registry).enqueue(
            EnqueueJobRequest.system(
                job_type="reaping_worker",
                payload={"value": "recovered"},
                run_after=wall_now - timedelta(seconds=20),
            )
        ).job
        session.commit()
        job_id = job.id
    with job_session_factory() as session:
        first_claim = JobDispatcher(
            session=session,
            registry=registry,
            queue_names=("default",),
        ).claim_next(
            worker_id=uuid4(),
            now=wall_now - timedelta(seconds=16),
        )
        assert first_claim is not None
        session.commit()

    async def scenario() -> None:
        worker = JobWorker(
            session_factory=job_session_factory,
            registry=registry,
            queue_names=("default",),
            reaper_interval_seconds=0.01,
        )
        task = asyncio.create_task(worker.run(poll_interval_seconds=0.01))
        try:
            for _index in range(500):
                with job_session_factory() as observer:
                    status = observer.scalar(
                        select(Job.status).where(Job.id == job_id)
                    )
                if status == "succeeded":
                    break
                await asyncio.sleep(0.01)
            else:
                raise AssertionError("daemon worker did not recover expired work")
        finally:
            worker.request_shutdown()
            await asyncio.wait_for(task, timeout=10)

    asyncio.run(scenario())

    with job_session_factory() as session:
        job = session.get(Job, job_id)
        attempts = list(
            session.scalars(
                select(JobAttempt)
                .where(JobAttempt.job_id == job_id)
                .order_by(JobAttempt.attempt_number)
            )
        )
        assert job is not None
        assert job.status == "succeeded"
        assert job.retry_count == 1
        assert [attempt.status for attempt in attempts] == ["expired", "succeeded"]


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
