"""Repository de job queue."""

from __future__ import annotations

import builtins
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Job, JobEvent
from adaptive_rag.db.models.job import utc_now


class JobRepository:
    """Acceso a jobs y eventos con transacciones controladas por caller."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        project_id: UUID,
        job_type: str,
        payload_json: Mapping[str, Any] | None = None,
        priority: int = 0,
        max_attempts: int = 3,
        run_after: datetime | None = None,
    ) -> Job:
        job = Job(
            project_id=project_id,
            job_type=job_type,
            payload_json=dict(payload_json) if payload_json is not None else None,
            priority=priority,
            max_attempts=max_attempts,
            run_after=run_after or utc_now(),
        )
        self._session.add(job)
        self._session.flush()
        self._add_event(project_id=project_id, job_id=job.id, event_type="created")
        self._session.flush()
        return job

    def get(self, *, project_id: UUID, job_id: UUID) -> Job | None:
        statement = select(Job).where(Job.id == job_id, Job.project_id == project_id)
        return self._session.scalars(statement).one_or_none()

    def lease_next(
        self,
        *,
        project_id: UUID,
        worker_id: str,
        lease_until: datetime,
        now: datetime,
        job_type: str | None = None,
    ) -> Job | None:
        statement = select(Job).where(
            Job.project_id == project_id,
            Job.status == "queued",
            Job.run_after <= now,
        )
        if job_type is not None:
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
            project_id=project_id,
            job_id=job.id,
            event_type="leased",
            message=worker_id,
        )
        self._session.flush()
        return job

    def complete(self, *, project_id: UUID, job_id: UUID) -> Job:
        job = self._require_job(project_id=project_id, job_id=job_id)
        job.status = "succeeded"
        job.locked_by = None
        job.locked_until = None
        job.last_error = None
        self._add_event(project_id=project_id, job_id=job.id, event_type="completed")
        self._session.flush()
        return job

    def fail(
        self,
        *,
        project_id: UUID,
        job_id: UUID,
        error_message: str,
        retry_after: datetime | None = None,
    ) -> Job:
        job = self._require_job(project_id=project_id, job_id=job_id)
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
            project_id=project_id,
            job_id=job.id,
            event_type=event_type,
            message=error_message,
        )
        self._session.flush()
        return job

    def block(self, *, project_id: UUID, job_id: UUID, reason: str) -> Job:
        job = self._require_job(project_id=project_id, job_id=job_id)
        job.status = "blocked"
        job.locked_by = None
        job.locked_until = None
        job.last_error = reason
        self._add_event(
            project_id=project_id,
            job_id=job.id,
            event_type="blocked",
            message=reason,
        )
        self._session.flush()
        return job

    def release_expired_leases(self, *, project_id: UUID, now: datetime) -> int:
        statement = select(Job).where(
            Job.project_id == project_id,
            Job.status == "running",
            Job.locked_until <= now,
        )
        jobs = builtins.list(self._session.scalars(statement))
        for job in jobs:
            job.status = "queued"
            job.locked_by = None
            job.locked_until = None
            self._add_event(project_id=project_id, job_id=job.id, event_type="released")
        self._session.flush()
        return len(jobs)

    def list_events(self, *, project_id: UUID, job_id: UUID) -> builtins.list[JobEvent]:
        statement = (
            select(JobEvent)
            .where(JobEvent.project_id == project_id, JobEvent.job_id == job_id)
            .order_by(JobEvent.created_at, JobEvent.id)
        )
        return builtins.list(self._session.scalars(statement))

    def _require_job(self, *, project_id: UUID, job_id: UUID) -> Job:
        job = self.get(project_id=project_id, job_id=job_id)
        if job is None:
            raise ValueError("job does not belong to project")
        return job

    def _add_event(
        self,
        *,
        project_id: UUID,
        job_id: UUID,
        event_type: str,
        message: str | None = None,
        extra_metadata: Mapping[str, Any] | None = None,
    ) -> JobEvent:
        event = JobEvent(
            project_id=project_id,
            job_id=job_id,
            event_type=event_type,
            message=message,
            extra_metadata=dict(extra_metadata) if extra_metadata is not None else None,
        )
        self._session.add(event)
        return event

