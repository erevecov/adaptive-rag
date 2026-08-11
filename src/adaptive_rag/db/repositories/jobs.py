"""Repository de job queue."""

from __future__ import annotations

import builtins
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from adaptive_rag.db.models import (
    Job,
    JobAttempt,
    JobEvent,
    JobQueue,
    JobQueueWorkspaceState,
)
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.jobs.errors import JobIdempotencyConflictError

OPEN_JOB_STATUSES = ("queued", "running", "blocked")
IDEMPOTENCY_CONSTRAINTS = {
    "uq_jobs_workspace_open_idempotency",
    "uq_jobs_system_open_idempotency",
}


class JobRepository:
    """Acceso a jobs y eventos con transacciones controladas por caller."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_queue(self, queue_name: str) -> JobQueue | None:
        return self._session.get(JobQueue, queue_name)

    def enqueue_validated(
        self,
        *,
        scope: str,
        workspace_id: UUID | None,
        queue_name: str,
        job_type: str,
        handler_version: int,
        payload_json: Mapping[str, Any],
        priority: int,
        max_retries: int,
        run_after: datetime,
        idempotency_key: str | None,
        idempotency_fingerprint: str | None,
        schedule_id: UUID | None,
        scheduled_for: datetime | None,
        concurrency_key: str | None,
    ) -> tuple[Job, bool]:
        """Insert one job without committing the caller's transaction."""

        if idempotency_key is not None:
            existing = self.find_open_idempotent(
                scope=scope,
                workspace_id=workspace_id,
                job_type=job_type,
                handler_version=handler_version,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                return self._match_idempotent(
                    existing=existing, fingerprint=idempotency_fingerprint
                )

        self._ensure_dispatch_state(
            queue_name=queue_name,
            scope_key=("system" if scope == "system" else f"workspace:{workspace_id}"),
        )
        job = Job(
            scope=scope,
            workspace_id=workspace_id,
            queue_name=queue_name,
            job_type=job_type,
            handler_version=handler_version,
            payload_json=dict(payload_json),
            priority=priority,
            max_retries=max_retries,
            max_attempts=max_retries + 1,
            run_after=run_after,
            idempotency_key=idempotency_key,
            idempotency_fingerprint=idempotency_fingerprint,
            schedule_id=schedule_id,
            scheduled_for=scheduled_for,
            concurrency_key=concurrency_key,
        )
        try:
            with self._session.begin_nested():
                self._session.add(job)
                self._session.flush()
        except IntegrityError as exc:
            if not self._is_idempotency_violation(exc):
                raise
            if idempotency_key is None:
                raise
            existing = self.find_open_idempotent(
                scope=scope,
                workspace_id=workspace_id,
                job_type=job_type,
                handler_version=handler_version,
                idempotency_key=idempotency_key,
            )
            if existing is None:
                raise
            return self._match_idempotent(
                existing=existing,
                fingerprint=idempotency_fingerprint,
            )

        self._add_scoped_event(job=job, event_type="created")
        self._add_scoped_event(job=job, event_type="queued")
        self._session.flush()
        return job, True

    def find_open_idempotent(
        self,
        *,
        scope: str,
        workspace_id: UUID | None,
        job_type: str,
        handler_version: int,
        idempotency_key: str,
    ) -> Job | None:
        statement = select(Job).where(
            Job.scope == scope,
            Job.job_type == job_type,
            Job.handler_version == handler_version,
            Job.idempotency_key == idempotency_key,
            Job.status.in_(OPEN_JOB_STATUSES),
        )
        if scope == "workspace":
            statement = statement.where(Job.workspace_id == workspace_id)
        else:
            statement = statement.where(Job.workspace_id.is_(None))
        return self._session.scalars(statement).one_or_none()

    def get_scoped(
        self, *, scope: str, workspace_id: UUID | None, job_id: UUID
    ) -> Job | None:
        statement = select(Job).where(Job.id == job_id, Job.scope == scope)
        if scope == "workspace":
            statement = statement.where(Job.workspace_id == workspace_id)
        else:
            statement = statement.where(Job.workspace_id.is_(None))
        return self._session.scalars(statement).one_or_none()

    def list_page(
        self,
        *,
        scope: str,
        workspace_id: UUID | None,
        limit: int,
        cursor: tuple[datetime, UUID] | None = None,
        status: str | None = None,
        queue_name: str | None = None,
        job_type: str | None = None,
        schedule_id: UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> builtins.list[Job]:
        statement = select(Job).where(Job.scope == scope)
        if scope == "workspace":
            statement = statement.where(Job.workspace_id == workspace_id)
        else:
            statement = statement.where(Job.workspace_id.is_(None))
        if status is not None:
            statement = statement.where(Job.status == status)
        if queue_name is not None:
            statement = statement.where(Job.queue_name == queue_name)
        if job_type is not None:
            statement = statement.where(Job.job_type == job_type)
        if schedule_id is not None:
            statement = statement.where(Job.schedule_id == schedule_id)
        if created_from is not None:
            statement = statement.where(Job.created_at >= created_from)
        if created_to is not None:
            statement = statement.where(Job.created_at <= created_to)
        if cursor is not None:
            cursor_time, cursor_id = cursor
            statement = statement.where(
                or_(
                    Job.created_at < cursor_time,
                    and_(Job.created_at == cursor_time, Job.id < cursor_id),
                )
            )
        statement = statement.order_by(Job.created_at.desc(), Job.id.desc()).limit(
            limit
        )
        return builtins.list(self._session.scalars(statement))

    def list_attempts(self, *, job_id: UUID, limit: int) -> builtins.list[JobAttempt]:
        statement = (
            select(JobAttempt)
            .where(JobAttempt.job_id == job_id)
            .order_by(JobAttempt.attempt_number.desc())
            .limit(limit)
        )
        return builtins.list(self._session.scalars(statement))

    def list_events_bounded(
        self, *, job_id: UUID, limit: int
    ) -> builtins.list[JobEvent]:
        statement = (
            select(JobEvent)
            .where(JobEvent.job_id == job_id)
            .order_by(JobEvent.created_at.desc(), JobEvent.id.desc())
            .limit(limit)
        )
        return builtins.list(self._session.scalars(statement))

    def create(
        self,
        *,
        workspace_id: UUID,
        job_type: str,
        payload_json: Mapping[str, Any] | None = None,
        priority: int = 0,
        max_attempts: int = 3,
        run_after: datetime | None = None,
    ) -> Job:
        job = Job(
            scope="workspace",
            workspace_id=workspace_id,
            queue_name="ingestion",
            handler_version=1,
            job_type=job_type,
            payload_json=dict(payload_json) if payload_json is not None else {},
            priority=priority,
            max_attempts=max_attempts,
            max_retries=max(0, min(25, max_attempts - 1)),
            run_after=run_after or utc_now(),
        )
        self._session.add(job)
        self._session.flush()
        self._add_event(workspace_id=workspace_id, job_id=job.id, event_type="created")
        self._session.flush()
        return job

    def get(self, *, workspace_id: UUID, job_id: UUID) -> Job | None:
        statement = select(Job).where(
            Job.id == job_id, Job.workspace_id == workspace_id
        )
        return self._session.scalars(statement).one_or_none()

    def list(
        self,
        *,
        workspace_id: UUID,
        status: str | None = None,
        statuses: Sequence[str] | None = None,
        job_type: str | None = None,
    ) -> builtins.list[Job]:
        if status is not None and statuses is not None:
            raise ValueError("pass status or statuses, not both")
        statement = select(Job).where(Job.workspace_id == workspace_id)
        if statuses is not None:
            statement = statement.where(Job.status.in_(tuple(statuses)))
        elif status is not None:
            statement = statement.where(Job.status == status)
        if job_type is not None:
            statement = statement.where(Job.job_type == job_type)
        statement = statement.order_by(Job.created_at, Job.id)
        return builtins.list(self._session.scalars(statement))

    def find_open_ingest_source(
        self,
        *,
        workspace_id: UUID,
        source_id: UUID,
    ) -> Job | None:
        """Return the oldest open ingest_source job for source_id, if any.

        Open means status in (queued, running). Payload match is application-level
        so SQLite and Postgres stay portable without JSON operator dialects.
        """
        source_key = str(source_id)
        for job in self.list(
            workspace_id=workspace_id,
            job_type="ingest_source",
            statuses=("queued", "running"),
        ):
            payload = job.payload_json or {}
            if payload.get("source_id") == source_key:
                return job
        return None

    def lease_next(
        self,
        *,
        workspace_id: UUID,
        worker_id: str,
        lease_until: datetime,
        now: datetime,
        job_type: str | None = None,
        job_types: Sequence[str] | None = None,
    ) -> Job | None:
        statement = select(Job).where(
            Job.workspace_id == workspace_id,
            Job.status == "queued",
            Job.run_after <= now,
        )
        if job_types is not None:
            statement = statement.where(Job.job_type.in_(tuple(job_types)))
        elif job_type is not None:
            statement = statement.where(Job.job_type == job_type)

        statement = (
            statement.order_by(Job.priority.desc(), Job.run_after, Job.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = self._session.scalars(statement).first()
        if job is None:
            return None

        job.status = "running"
        job.locked_by = worker_id
        job.locked_until = lease_until
        job.attempts += 1
        self._add_event(
            workspace_id=workspace_id,
            job_id=job.id,
            event_type="leased",
            message=worker_id,
        )
        self._session.flush()
        return job

    def complete(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
        worker_id: str | None = None,
    ) -> Job:
        job = self._require_job(workspace_id=workspace_id, job_id=job_id)
        self._assert_lease_owner(job, worker_id=worker_id)
        job.status = "succeeded"
        job.locked_by = None
        job.locked_until = None
        job.last_error = None
        self._add_event(
            workspace_id=workspace_id, job_id=job.id, event_type="completed"
        )
        self._session.flush()
        return job

    def fail(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
        error_message: str,
        retry_after: datetime | None = None,
        worker_id: str | None = None,
    ) -> Job:
        job = self._require_job(workspace_id=workspace_id, job_id=job_id)
        self._assert_lease_owner(job, worker_id=worker_id)
        job.locked_by = None
        job.locked_until = None
        job.last_error = error_message

        if job.attempts >= job.max_attempts:
            job.status = "dead_letter"
            event_type = "dead_lettered"
        else:
            job.status = "queued"
            job.run_after = retry_after or utc_now()
            event_type = "failed_attempt"

        self._add_event(
            workspace_id=workspace_id,
            job_id=job.id,
            event_type=event_type,
            message=error_message,
        )
        self._session.flush()
        return job

    def block(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
        reason: str,
        worker_id: str | None = None,
    ) -> Job:
        job = self._require_job(workspace_id=workspace_id, job_id=job_id)
        self._assert_lease_owner(job, worker_id=worker_id)
        job.status = "blocked"
        job.locked_by = None
        job.locked_until = None
        job.last_error = reason
        self._add_event(
            workspace_id=workspace_id,
            job_id=job.id,
            event_type="blocked",
            message=reason,
        )
        self._session.flush()
        return job

    def requeue(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
        run_after: datetime | None = None,
        reset_attempts: bool = True,
    ) -> Job:
        job = self._require_job(workspace_id=workspace_id, job_id=job_id)
        if job.status not in {"blocked", "dead_letter"}:
            raise ValueError("job is not retryable")

        job.status = "queued"
        job.locked_by = None
        job.locked_until = None
        job.last_error = None
        job.run_after = run_after or utc_now()
        if reset_attempts:
            job.attempts = 0
        self._add_event(workspace_id=workspace_id, job_id=job.id, event_type="retried")
        self._session.flush()
        return job

    def release_expired_leases(self, *, workspace_id: UUID, now: datetime) -> int:
        statement = select(Job).where(
            Job.workspace_id == workspace_id,
            Job.status == "running",
            Job.locked_until <= now,
        )
        jobs = builtins.list(self._session.scalars(statement))
        for job in jobs:
            # Lease already counted the attempt in lease_next; consult it so
            # crashed workers cannot requeue forever past max_attempts.
            job.locked_by = None
            job.locked_until = None
            if job.attempts >= job.max_attempts:
                job.status = "dead_letter"
                if job.last_error is None:
                    job.last_error = "lease expired"
                self._add_event(
                    workspace_id=workspace_id,
                    job_id=job.id,
                    event_type="released",
                )
                self._add_event(
                    workspace_id=workspace_id,
                    job_id=job.id,
                    event_type="dead_lettered",
                    message=job.last_error,
                )
            else:
                job.status = "queued"
                self._add_event(
                    workspace_id=workspace_id,
                    job_id=job.id,
                    event_type="released",
                )
        self._session.flush()
        return len(jobs)

    def list_events(
        self, *, workspace_id: UUID, job_id: UUID
    ) -> builtins.list[JobEvent]:
        statement = (
            select(JobEvent)
            .where(JobEvent.workspace_id == workspace_id, JobEvent.job_id == job_id)
            .order_by(JobEvent.created_at, JobEvent.id)
        )
        return builtins.list(self._session.scalars(statement))

    def _require_job(self, *, workspace_id: UUID, job_id: UUID) -> Job:
        job = self.get(workspace_id=workspace_id, job_id=job_id)
        if job is None:
            raise ValueError("job does not belong to workspace")
        return job

    def _assert_lease_owner(self, job: Job, *, worker_id: str | None) -> None:
        """Reject transitions from a non-owner when a lease is active.

        Unlocked jobs (locked_by is None) stay writable so admin paths and
        tests can complete/fail/block without a lease.
        """

        if job.locked_by is None:
            return
        if worker_id is None or worker_id != job.locked_by:
            raise ValueError("job is locked by another worker")

    def _add_event(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
        event_type: str,
        message: str | None = None,
        extra_metadata: Mapping[str, Any] | None = None,
    ) -> JobEvent:
        event = JobEvent(
            scope="workspace",
            workspace_id=workspace_id,
            job_id=job_id,
            event_type=event_type,
            message=message,
            extra_metadata=dict(extra_metadata) if extra_metadata is not None else None,
        )
        self._session.add(event)
        return event

    def _add_scoped_event(self, *, job: Job, event_type: str) -> JobEvent:
        event = JobEvent(
            scope=job.scope,
            workspace_id=job.workspace_id,
            job_id=job.id,
            event_type=event_type,
        )
        self._session.add(event)
        return event

    def _ensure_dispatch_state(self, *, queue_name: str, scope_key: str) -> None:
        values = {"queue_name": queue_name, "scope_key": scope_key}
        dialect_name = self._session.get_bind().dialect.name
        if dialect_name == "postgresql":
            postgres_statement = postgresql_insert(JobQueueWorkspaceState).values(
                **values
            )
            self._session.execute(
                postgres_statement.on_conflict_do_nothing(
                    index_elements=["queue_name", "scope_key"]
                )
            )
            return
        if dialect_name == "sqlite":
            sqlite_statement = sqlite_insert(JobQueueWorkspaceState).values(**values)
            self._session.execute(
                sqlite_statement.on_conflict_do_nothing(
                    index_elements=["queue_name", "scope_key"]
                )
            )
            return
        if self._session.get(JobQueueWorkspaceState, (queue_name, scope_key)) is None:
            self._session.add(JobQueueWorkspaceState(**values))

    @staticmethod
    def _match_idempotent(
        *, existing: Job, fingerprint: str | None
    ) -> tuple[Job, bool]:
        if existing.idempotency_fingerprint != fingerprint:
            raise JobIdempotencyConflictError(
                "Idempotency key is already used by different job parameters"
            )
        return existing, False

    @staticmethod
    def _is_idempotency_violation(exc: IntegrityError) -> bool:
        diagnostic = getattr(exc.orig, "diag", None)
        constraint_name = getattr(diagnostic, "constraint_name", None)
        return constraint_name in IDEMPOTENCY_CONSTRAINTS
