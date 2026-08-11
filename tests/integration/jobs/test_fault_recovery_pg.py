"""Real PostgreSQL failure recovery, polling, and least-privilege checks."""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine, create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.db.models import Job, JobAttempt, JobEvent, Workspace
from adaptive_rag.db.repositories import WorkspaceRepository
from adaptive_rag.db.session import create_session_factory
from adaptive_rag.jobs import JobContext, JobHandlerDefinition, JobRegistry, RetryPolicy
from adaptive_rag.jobs.reaper import JobReaper
from adaptive_rag.jobs.service import EnqueueJobRequest, JobService
from adaptive_rag.jobs.transitions import JobTransitions
from adaptive_rag.jobs.worker import JobWorker

REPO_ROOT = Path(__file__).resolve().parents[3]
PROCESS_HARNESS = Path(__file__).with_name("_fault_worker_process.py")


class FaultPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str


def _registry(*, read_factory: sessionmaker[Session] | None = None) -> JobRegistry:
    def finish(context: JobContext, payload: FaultPayload) -> dict[str, str]:
        if read_factory is not None:
            with read_factory() as session:
                assert session.get(Workspace, context.workspace_id) is not None
        return {"value": payload.value}

    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="fault_worker",
            version=1,
            payload_model=FaultPayload,
            handler=finish,
            queue_name="default",
            allowed_scopes=frozenset({"workspace", "system"}),
            retry_policy=RetryPolicy(
                max_retries=2,
                base_delay_seconds=1,
                max_delay_seconds=1,
            ),
            lease_seconds=15,
        )
    )
    return registry


def test_sigkill_reaps_and_fences_the_obsolete_attempt(
    job_database_url: str,
    job_session_factory: sessionmaker[Session],
) -> None:
    registry = _registry()
    enqueued_at = datetime.now(UTC)
    with job_session_factory() as session:
        job = JobService(session=session, registry=registry).enqueue(
            EnqueueJobRequest.system(
                job_type="fault_worker",
                payload={"value": "recovered"},
                run_after=enqueued_at,
            )
        ).job
        session.commit()
        job_id = job.id

    process = subprocess.Popen(
        ["uv", "run", "python", str(PROCESS_HARNESS), job_database_url],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    first_attempt_id = None
    try:
        for _index in range(200):
            with job_session_factory() as observer:
                observed = observer.get(Job, job_id)
                if observed is not None and observed.status == "running":
                    first_attempt_id = observed.current_attempt_id
                    break
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise AssertionError(
                    f"fault worker exited before claim\n{stdout}\n{stderr}"
                )
            time.sleep(0.025)
        else:
            raise AssertionError("subprocess did not claim the job")
    finally:
        process.kill()
        process.wait(timeout=10)

    assert first_attempt_id is not None
    recovery_time = datetime.now(UTC) + timedelta(seconds=16)
    with job_session_factory() as session:
        assert (
            JobReaper(
                session=session,
                registry=registry,
                random_source=lambda: 0.0,
            ).run_once(now=recovery_time)
            == 1
        )
        session.commit()

    report = JobWorker(
        session_factory=job_session_factory,
        registry=registry,
        queue_names=("default",),
        now_source=lambda: recovery_time + timedelta(seconds=1),
    ).run_once_sync()
    assert report.status == "succeeded"

    with job_session_factory() as session:
        stale_completion = JobTransitions(
            session=session,
            registry=registry,
        ).complete(
            job_id=job_id,
            attempt_id=first_attempt_id,
            result={"value": "stale"},
            now=recovery_time + timedelta(seconds=2),
        )
        session.commit()
        attempts = list(
            session.scalars(
                select(JobAttempt)
                .where(JobAttempt.job_id == job_id)
                .order_by(JobAttempt.attempt_number)
            )
        )
        fenced_events = session.scalar(
            select(func.count(JobEvent.id)).where(
                JobEvent.job_id == job_id,
                JobEvent.event_type == "fenced_write_rejected",
            )
        )
        final_job = session.get(Job, job_id)

    assert stale_completion is False
    assert final_job is not None
    assert final_job.status == "succeeded"
    assert final_job.result_json == {"value": "recovered"}
    assert [attempt.status for attempt in attempts] == ["expired", "succeeded"]
    assert fenced_events == 1


def test_worker_polling_recovers_when_notify_trigger_is_disabled(
    job_engine: Engine,
    job_session_factory: sessionmaker[Session],
) -> None:
    async def scenario() -> None:
        registry = _registry()
        worker = JobWorker(
            session_factory=job_session_factory,
            registry=registry,
            queue_names=("default",),
        )
        with job_engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE jobs DISABLE TRIGGER trg_jobs_notify_insert")
            )
        task = asyncio.create_task(worker.run(poll_interval_seconds=0.05))
        try:
            await asyncio.sleep(0.02)
            with job_session_factory() as session:
                job = JobService(session=session, registry=registry).enqueue(
                    EnqueueJobRequest.system(
                        job_type="fault_worker",
                        payload={"value": "polled"},
                    )
                ).job
                session.commit()
                job_id = job.id
            for _index in range(200):
                with job_session_factory() as observer:
                    status = observer.scalar(
                        select(Job.status).where(Job.id == job_id)
                    )
                if status == "succeeded":
                    break
                await asyncio.sleep(0.025)
            else:
                raise AssertionError("polling fallback did not execute the job")
        finally:
            worker.request_shutdown()
            await asyncio.wait_for(task, timeout=10)
            with job_engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE jobs ENABLE TRIGGER trg_jobs_notify_insert")
                )

    asyncio.run(scenario())


def test_worker_operates_with_least_privilege_role(
    job_database_url: str,
    job_engine: Engine,
    job_session_factory: sessionmaker[Session],
) -> None:
    role = "adaptive_rag_job_worker_test"
    password = "job-worker-test-password"
    table_grants = (
        "job_queues, job_queue_workspace_state, jobs, job_attempts, "
        "job_events, job_workers"
    )
    database_name = make_url(job_database_url).database
    assert database_name is not None
    with job_engine.begin() as connection:
        connection.execute(text(f"DROP ROLE IF EXISTS {role}"))
        connection.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD '{password}'"))
        connection.execute(
            text(f'GRANT CONNECT ON DATABASE "{database_name}" TO {role}')
        )
        connection.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        connection.execute(
            text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table_grants} TO {role}")
        )
        connection.execute(text(f"GRANT SELECT ON workspaces TO {role}"))

    limited_url = make_url(job_database_url).set(username=role, password=password)
    limited_engine = create_engine(limited_url, pool_pre_ping=True)
    limited_factory = create_session_factory(limited_engine)
    registry = _registry(read_factory=limited_factory)
    try:
        with job_session_factory() as session:
            workspace = WorkspaceRepository(session).create(name="least-privilege")
            job = JobService(session=session, registry=registry).enqueue(
                EnqueueJobRequest.workspace(
                    workspace_id=workspace.id,
                    job_type="fault_worker",
                    payload={"value": "limited"},
                )
            ).job
            session.commit()
            job_id = job.id

        report = JobWorker(
            session_factory=limited_factory,
            registry=registry,
            queue_names=("default",),
        ).run_once_sync()
        assert report.status == "succeeded"

        with limited_engine.connect() as connection:
            can_create = connection.scalar(
                text("SELECT has_schema_privilege(current_user, 'public', 'CREATE')")
            )
            can_mutate_migrations = connection.scalar(
                text(
                    "SELECT has_table_privilege(current_user, "
                    "'alembic_version', 'UPDATE')"
                )
            )
            assert can_create is False
            assert can_mutate_migrations is False
            connection.rollback()
            with pytest.raises(DBAPIError):
                connection.execute(
                    text("UPDATE alembic_version SET version_num = version_num")
                )

        with job_session_factory() as session:
            stored = session.get(Job, job_id)
            assert stored is not None
            assert stored.status == "succeeded"
    finally:
        limited_engine.dispose()
        with job_engine.begin() as connection:
            connection.execute(text(f"DROP OWNED BY {role}"))
            connection.execute(text(f"DROP ROLE {role}"))
