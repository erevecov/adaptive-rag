"""PostgreSQL runtime primitives for fair, fenced job execution."""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select, tuple_, update
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from adaptive_rag.db.models import (
    Job,
    JobAttempt,
    JobEvent,
    JobQueue,
    JobQueueWorkspaceState,
)
from adaptive_rag.jobs.types import HandlerKey


@dataclass(frozen=True, slots=True)
class RuntimeHandlerConfig:
    lease_seconds: int
    handler_limit: int | None
    key_limit: int | None


@dataclass(frozen=True, slots=True)
class RuntimeClaim:
    job_id: UUID
    attempt_id: UUID
    worker_id: UUID
    scope: str
    workspace_id: UUID | None
    queue_name: str
    job_type: str
    handler_version: int
    payload_json: dict[str, Any]
    idempotency_key: str | None
    retry_count: int
    max_retries: int
    lease_expires_at: datetime


class JobRuntimeRepository:
    """Short-transaction claim and fencing operations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def claim_from_queue(
        self,
        *,
        queue_name: str,
        worker_id: UUID,
        handler_configs: Mapping[HandlerKey, RuntimeHandlerConfig],
        advisory_lock_ids: Mapping[HandlerKey, int],
        key_lock_id_factory: Callable[[str, str, str], int],
        now: datetime,
        workspace_id: UUID | None = None,
    ) -> RuntimeClaim | None:
        queue = self._session.scalars(
            select(JobQueue).where(JobQueue.name == queue_name).with_for_update()
        ).one_or_none()
        if queue is None or queue.paused_at is not None or not handler_configs:
            return None
        if self._at_capacity(
            limit=queue.global_concurrency_limit,
            filters=(Job.queue_name == queue_name,),
        ):
            return None

        state_query = select(JobQueueWorkspaceState).where(
            JobQueueWorkspaceState.queue_name == queue_name
        )
        if workspace_id is not None:
            state_query = state_query.where(
                JobQueueWorkspaceState.scope_key == f"workspace:{workspace_id}"
            )
        states = list(
            self._session.scalars(
                state_query.order_by(
                    JobQueueWorkspaceState.last_claimed_at.asc().nullsfirst(),
                    JobQueueWorkspaceState.created_at,
                    JobQueueWorkspaceState.scope_key,
                ).with_for_update(skip_locked=True)
            )
        )
        supported = tuple(handler_configs)
        for state in states:
            scope_filters = self._scope_filters(state.scope_key)
            if self._at_capacity(
                limit=queue.workspace_concurrency_limit,
                filters=(Job.queue_name == queue_name, *scope_filters),
            ):
                continue
            candidates = list(
                self._session.scalars(
                    select(Job)
                    .where(
                        Job.queue_name == queue_name,
                        Job.status == "queued",
                        Job.run_after <= now,
                        tuple_(Job.job_type, Job.handler_version).in_(supported),
                        *scope_filters,
                    )
                    .order_by(
                        Job.priority.desc(),
                        Job.run_after,
                        Job.created_at,
                        Job.id,
                    )
                    .limit(100)
                    .with_for_update(skip_locked=True)
                )
            )
            for job in candidates:
                handler_key = (job.job_type, job.handler_version)
                config = handler_configs[handler_key]
                lock_ids = []
                if config.handler_limit is not None:
                    lock_ids.append(advisory_lock_ids[handler_key])
                if config.key_limit is not None and job.concurrency_key is not None:
                    lock_ids.append(
                        key_lock_id_factory(
                            job.job_type,
                            str(job.handler_version),
                            job.concurrency_key,
                        )
                    )
                self._acquire_advisory_locks(lock_ids)
                if self._at_capacity(
                    limit=config.handler_limit,
                    filters=(
                        Job.job_type == job.job_type,
                        Job.handler_version == job.handler_version,
                    ),
                ):
                    continue
                if job.concurrency_key is not None and self._at_capacity(
                    limit=config.key_limit,
                    filters=(
                        Job.job_type == job.job_type,
                        Job.handler_version == job.handler_version,
                        Job.concurrency_key == job.concurrency_key,
                    ),
                ):
                    continue
                return self._claim(
                    job=job,
                    state=state,
                    worker_id=worker_id,
                    lease_seconds=config.lease_seconds,
                    now=now,
                    all_states=states,
                )
        return None

    def heartbeat(
        self,
        *,
        job_id: UUID,
        attempt_id: UUID,
        now: datetime,
        lease_expires_at: datetime,
    ) -> bool:
        updated_job = self._session.execute(
            update(Job)
            .where(
                Job.id == job_id,
                Job.status == "running",
                Job.current_attempt_id == attempt_id,
            )
            .values(locked_until=lease_expires_at, updated_at=now)
            .returning(Job.id)
        ).scalar_one_or_none()
        if updated_job is None:
            return False
        self._session.execute(
            update(JobAttempt)
            .where(JobAttempt.id == attempt_id, JobAttempt.status == "running")
            .values(heartbeat_at=now, lease_expires_at=lease_expires_at)
        )
        return True

    def update_progress(
        self,
        *,
        job_id: UUID,
        attempt_id: UUID,
        progress: Mapping[str, object],
        now: datetime,
        minimum_interval: timedelta = timedelta(seconds=1),
    ) -> bool:
        current = self._session.execute(
            select(Job.id).where(
                Job.id == job_id,
                Job.status == "running",
                Job.current_attempt_id == attempt_id,
            )
        ).scalar_one_or_none()
        if current is None:
            return False
        updated_attempt = self._session.execute(
            update(JobAttempt)
            .where(
                JobAttempt.id == attempt_id,
                JobAttempt.status == "running",
                (
                    (JobAttempt.progress_updated_at.is_(None))
                    | (JobAttempt.progress_updated_at <= now - minimum_interval)
                ),
            )
            .values(progress_json=dict(progress), progress_updated_at=now)
            .returning(JobAttempt.id)
        ).scalar_one_or_none()
        return updated_attempt is not None

    def finish_fenced(
        self,
        *,
        job_id: UUID,
        attempt_id: UUID,
        now: datetime,
        job_status: str,
        attempt_status: str,
        result_json: object | None = None,
    ) -> bool:
        values: dict[str, object] = {
            "status": job_status,
            "current_attempt_id": None,
            "locked_by": None,
            "locked_until": None,
            "finished_at": now,
            "updated_at": now,
        }
        if result_json is not None:
            values["result_json"] = result_json
        updated_job = self._session.execute(
            update(Job)
            .where(
                Job.id == job_id,
                Job.status == "running",
                Job.current_attempt_id == attempt_id,
            )
            .values(**values)
            .returning(Job.id)
        ).scalar_one_or_none()
        if updated_job is None:
            return False
        self._session.execute(
            update(JobAttempt)
            .where(JobAttempt.id == attempt_id, JobAttempt.status == "running")
            .values(status=attempt_status, finished_at=now)
        )
        return True

    def _claim(
        self,
        *,
        job: Job,
        state: JobQueueWorkspaceState,
        worker_id: UUID,
        lease_seconds: int,
        now: datetime,
        all_states: Collection[JobQueueWorkspaceState],
    ) -> RuntimeClaim:
        attempt_id = uuid4()
        lease_expires_at = now + timedelta(seconds=lease_seconds)
        attempt_number = job.attempt_count + 1
        attempt = JobAttempt(
            id=attempt_id,
            job_id=job.id,
            scope=job.scope,
            workspace_id=job.workspace_id,
            attempt_number=attempt_number,
            worker_id=worker_id,
            status="running",
            started_at=now,
            heartbeat_at=now,
            lease_expires_at=lease_expires_at,
        )
        self._session.add(attempt)
        self._session.flush()
        job.status = "running"
        job.current_attempt_id = attempt_id
        job.attempt_count = attempt_number
        job.attempts = attempt_number
        job.locked_by = str(worker_id)
        job.locked_until = lease_expires_at
        job.version += 1
        state.last_claimed_at = self._next_cursor_time(now=now, states=all_states)
        self._session.add(
            JobEvent(
                scope=job.scope,
                workspace_id=job.workspace_id,
                job_id=job.id,
                attempt_id=attempt_id,
                event_type="leased",
                message=str(worker_id),
            )
        )
        self._session.flush()
        return RuntimeClaim(
            job_id=job.id,
            attempt_id=attempt_id,
            worker_id=worker_id,
            scope=job.scope,
            workspace_id=job.workspace_id,
            queue_name=job.queue_name,
            job_type=job.job_type,
            handler_version=job.handler_version,
            payload_json=dict(job.payload_json),
            idempotency_key=job.idempotency_key,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
            lease_expires_at=lease_expires_at,
        )

    def _at_capacity(
        self,
        *,
        limit: int | None,
        filters: tuple[ColumnElement[bool], ...],
    ) -> bool:
        if limit is None:
            return False
        running = self._session.scalar(
            select(func.count(Job.id)).where(Job.status == "running", *filters)
        )
        return int(running or 0) >= limit

    def _acquire_advisory_locks(self, lock_ids: Collection[int]) -> None:
        if self._session.get_bind().dialect.name != "postgresql":
            return
        for lock_id in sorted(set(lock_ids)):
            self._session.execute(select(func.pg_advisory_xact_lock(lock_id)))

    @staticmethod
    def _scope_filters(scope_key: str) -> tuple[ColumnElement[bool], ...]:
        if scope_key == "system":
            return (Job.scope == "system", Job.workspace_id.is_(None))
        prefix = "workspace:"
        if not scope_key.startswith(prefix):
            raise ValueError(f"Invalid queue scope key: {scope_key}")
        workspace_id = UUID(scope_key[len(prefix) :])
        return (Job.scope == "workspace", Job.workspace_id == workspace_id)

    @staticmethod
    def _next_cursor_time(
        *, now: datetime, states: Collection[JobQueueWorkspaceState]
    ) -> datetime:
        latest = max(
            (
                state.last_claimed_at
                for state in states
                if state.last_claimed_at is not None
            ),
            default=None,
        )
        if latest is not None and latest >= now:
            return latest + timedelta(microseconds=1)
        return now


__all__ = ["JobRuntimeRepository", "RuntimeClaim", "RuntimeHandlerConfig"]
