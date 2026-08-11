"""Release acceptance workload for the complete PostgreSQL job platform."""

from __future__ import annotations

import asyncio
import json
import time
from collections import Counter

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.db.models import Job, JobAttempt, JobEvent, JobQueue, JobWorker
from adaptive_rag.db.repositories import WorkspaceRepository
from adaptive_rag.jobs import JobContext, JobHandlerDefinition, JobRegistry
from adaptive_rag.jobs.service import EnqueueJobRequest, JobService
from adaptive_rag.jobs.worker import JobWorker as RuntimeWorker

JOB_COUNT = 500
WORKSPACE_COUNT = 4
PROCESS_COUNT = 4
LOCAL_CONCURRENCY = 8
GLOBAL_CONCURRENCY = 16
WORKSPACE_CONCURRENCY = 8


class AcceptancePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int


def test_acceptance_drains_500_jobs_fairly_with_bounded_connections(
    job_engine: Engine,
    job_session_factory: sessionmaker[Session],
) -> None:
    async def handler(
        _context: JobContext, payload: AcceptancePayload
    ) -> dict[str, int]:
        await asyncio.sleep(0.02)
        return {"sequence": payload.sequence}

    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="acceptance_echo",
            version=1,
            payload_model=AcceptancePayload,
            handler=handler,
            queue_name="default",
            allowed_scopes=frozenset({"workspace"}),
            lease_seconds=30,
        )
    )
    with job_session_factory() as session:
        queue = session.get(JobQueue, "default")
        assert queue is not None
        queue.global_concurrency_limit = GLOBAL_CONCURRENCY
        queue.workspace_concurrency_limit = WORKSPACE_CONCURRENCY
        workspaces = [
            WorkspaceRepository(session).create(name=f"acceptance-{index}")
            for index in range(WORKSPACE_COUNT)
        ]
        session.flush()
        for sequence in range(JOB_COUNT):
            JobService(session=session, registry=registry).enqueue(
                EnqueueJobRequest.workspace(
                    workspace_id=workspaces[sequence % WORKSPACE_COUNT].id,
                    job_type="acceptance_echo",
                    payload={"sequence": sequence},
                )
            )
        workspace_ids = [workspace.id for workspace in workspaces]
        session.commit()

    async def run_workload() -> dict[str, float | int]:
        workers = [
            RuntimeWorker(
                session_factory=job_session_factory,
                registry=registry,
                queue_names=("default",),
                max_concurrency=LOCAL_CONCURRENCY,
                heartbeat_interval_seconds=5,
            )
            for _index in range(PROCESS_COUNT)
        ]
        tasks = [
            asyncio.create_task(worker.run(poll_interval_seconds=0.02))
            for worker in workers
        ]
        started = time.perf_counter()
        max_running = 0
        max_workspace_running = 0
        max_connections = 0
        max_transaction_age_seconds = 0.0
        try:
            for _index in range(6000):
                for task in tasks:
                    if task.done() and task.exception() is not None:
                        raise task.exception()  # type: ignore[misc]
                with job_session_factory() as observer:
                    statuses = Counter(
                        {
                            status: int(count)
                            for status, count in observer.execute(
                                select(Job.status, func.count(Job.id)).group_by(
                                    Job.status
                                )
                            )
                        }
                    )
                    running_by_workspace = [
                        int(count)
                        for (count,) in observer.execute(
                            select(func.count(Job.id))
                            .where(Job.status == "running")
                            .group_by(Job.workspace_id)
                        )
                    ]
                    max_running = max(max_running, statuses["running"])
                    max_workspace_running = max(
                        max_workspace_running,
                        max(running_by_workspace, default=0),
                    )
                    connections = observer.scalar(
                        text(
                            "SELECT count(*) FROM pg_stat_activity "
                            "WHERE datname = current_database()"
                        )
                    )
                    max_connections = max(max_connections, int(connections or 0))
                    transaction_age = observer.scalar(
                        text(
                            "SELECT COALESCE(max(EXTRACT(EPOCH FROM "
                            "(clock_timestamp() - xact_start))), 0) "
                            "FROM pg_stat_activity WHERE datname = current_database() "
                            "AND xact_start IS NOT NULL"
                        )
                    )
                    max_transaction_age_seconds = max(
                        max_transaction_age_seconds,
                        float(transaction_age or 0),
                    )
                if statuses["succeeded"] == JOB_COUNT:
                    break
                await asyncio.sleep(0.01)
            else:
                raise AssertionError(f"workload did not drain: {dict(statuses)}")
        finally:
            for worker in workers:
                worker.request_shutdown()
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=20)
        return {
            "duration_seconds": round(time.perf_counter() - started, 3),
            "max_connections": max_connections,
            "max_running": max_running,
            "max_transaction_age_seconds": round(
                max_transaction_age_seconds, 6
            ),
            "max_workspace_running": max_workspace_running,
        }

    evidence = asyncio.run(run_workload())

    with job_session_factory() as session:
        statuses = Counter(
            {
                status: int(count)
                for status, count in session.execute(
                    select(Job.status, func.count(Job.id)).group_by(Job.status)
                )
            }
        )
        succeeded_by_workspace = {
            workspace_id: int(count)
            for workspace_id, count in session.execute(
                select(Job.workspace_id, func.count(Job.id))
                .where(Job.status == "succeeded")
                .group_by(Job.workspace_id)
            )
        }
        attempt_count = int(
            session.scalar(select(func.count(JobAttempt.id))) or 0
        )
        completion_count = int(
            session.scalar(
                select(func.count(JobEvent.id)).where(
                    JobEvent.event_type == "completed"
                )
            )
            or 0
        )
        presences = list(
            session.scalars(
                select(JobWorker).where(JobWorker.max_concurrency == LOCAL_CONCURRENCY)
            )
        )
        queue_latencies = [
            (attempt.started_at - job.created_at).total_seconds()
            for job, attempt in session.execute(
                select(Job, JobAttempt).join(JobAttempt, JobAttempt.job_id == Job.id)
            )
        ]

    evidence["max_queue_latency_seconds"] = round(max(queue_latencies), 6)
    evidence["average_queue_latency_seconds"] = round(
        sum(queue_latencies) / len(queue_latencies), 6
    )

    assert statuses == Counter({"succeeded": JOB_COUNT})
    assert succeeded_by_workspace == {
        workspace_id: JOB_COUNT // WORKSPACE_COUNT for workspace_id in workspace_ids
    }
    assert attempt_count == JOB_COUNT
    assert completion_count == JOB_COUNT
    assert evidence["max_running"] <= GLOBAL_CONCURRENCY
    assert evidence["max_workspace_running"] <= WORKSPACE_CONCURRENCY
    assert evidence["max_connections"] <= 40
    assert len(presences) == PROCESS_COUNT
    assert all(presence.shutdown_at is not None for presence in presences)
    print("JOB_PLATFORM_ACCEPTANCE " + json.dumps(evidence, sort_keys=True))
