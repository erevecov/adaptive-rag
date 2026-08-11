"""Bounded recovery of expired current job attempts."""

from __future__ import annotations

import random
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Job, JobAttempt, JobEvent
from adaptive_rag.jobs.errors import UnknownJobHandlerError
from adaptive_rag.jobs.registry import JobRegistry
from adaptive_rag.jobs.types import retry_delay_seconds


class JobReaper:
    """Expires leased attempts once, using row locks as the replica fence."""

    def __init__(
        self,
        *,
        session: Session,
        registry: JobRegistry,
        random_source: Callable[[], float] = random.random,
    ) -> None:
        self._session = session
        self._registry = registry
        self._random_source = random_source

    def run_once(self, *, now: datetime, batch_size: int = 100) -> int:
        if not 1 <= batch_size <= 1000:
            raise ValueError("batch_size must be within [1, 1000]")
        attempts = list(
            self._session.scalars(
                select(JobAttempt)
                .join(
                    Job,
                    (Job.id == JobAttempt.job_id)
                    & (Job.current_attempt_id == JobAttempt.id),
                )
                .where(
                    Job.status == "running",
                    JobAttempt.status == "running",
                    JobAttempt.lease_expires_at <= now,
                )
                .order_by(JobAttempt.lease_expires_at, JobAttempt.id)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
        )
        reaped = 0
        for attempt in attempts:
            job = self._session.get(Job, attempt.job_id)
            if (
                job is None
                or job.status != "running"
                or job.current_attempt_id != attempt.id
                or attempt.status != "running"
            ):
                continue
            job.retry_count += 1
            job.last_error = "attempt lease expired"
            job.last_error_code = "attempt_expired"
            job.last_error_message = "attempt lease expired"
            if job.retry_count <= job.max_retries:
                try:
                    definition = self._registry.get(
                        job.job_type, job.handler_version
                    )
                except UnknownJobHandlerError:
                    job.status = "blocked"
                    job.last_error = "handler version is not available"
                    job.last_error_code = "unsupported_handler_version"
                    job.last_error_message = "handler version is not available"
                    job.finished_at = None
                else:
                    delay = retry_delay_seconds(
                        definition.retry_policy,
                        job.retry_count - 1,
                        random_value=self._random_source(),
                    )
                    job.status = "queued"
                    job.run_after = now + timedelta(seconds=delay)
                    job.finished_at = None
            else:
                job.status = "dead_letter"
                job.finished_at = now
            job.current_attempt_id = None
            job.locked_by = None
            job.locked_until = None
            job.version += 1
            attempt.status = "expired"
            attempt.finished_at = now
            attempt.error_code = job.last_error_code
            attempt.error_message = job.last_error_message
            self._session.add(
                JobEvent(
                    scope=job.scope,
                    workspace_id=job.workspace_id,
                    job_id=job.id,
                    attempt_id=attempt.id,
                    event_type="expired",
                    message="attempt lease expired",
                    extra_metadata={"next_status": job.status},
                )
            )
            reaped += 1
        self._session.flush()
        return reaped


__all__ = ["JobReaper"]
