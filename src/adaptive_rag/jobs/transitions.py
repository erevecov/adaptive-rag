"""Explicit fenced state transitions for running job attempts."""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Job, JobAttempt, JobEvent
from adaptive_rag.jobs.registry import JobRegistry
from adaptive_rag.jobs.types import retry_delay_seconds

_TRANSITIONS = {
    ("running", "complete"): "succeeded",
    ("running", "retryable_failure"): "queued",
    ("running", "block"): "blocked",
    ("running", "permanent_failure"): "dead_letter",
    ("running", "confirm_cancelled"): "cancelled",
    ("queued", "cancel"): "cancelled",
    ("blocked", "cancel"): "cancelled",
    ("blocked", "unblock"): "queued",
    ("dead_letter", "retry"): "queued",
}


def transition_target(start: str, operation: str) -> str:
    try:
        return _TRANSITIONS[(start, operation)]
    except KeyError as exc:
        raise ValueError(f"Cannot {operation} a {start} job") from exc


class JobTransitions:
    """Mutates a running job only when its attempt fencing token is current."""

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

    def complete(
        self,
        *,
        job_id: UUID,
        attempt_id: UUID,
        result: object,
        now: datetime,
    ) -> bool:
        job = self._lock_current(job_id=job_id, attempt_id=attempt_id)
        if job is None:
            return False
        validated_result = self._registry.validate_result(
            job.job_type, job.handler_version, result
        )
        job.status = "succeeded"
        job.result_json = validated_result  # type: ignore[assignment]
        job.finished_at = now
        job.last_error = None
        job.last_error_code = None
        job.last_error_message = None
        event_type = (
            "completed_after_cancel_request"
            if job.cancellation_requested_at is not None
            else "completed"
        )
        self._finish_attempt(
            job=job,
            attempt_id=attempt_id,
            attempt_status="succeeded",
            now=now,
        )
        self._event(job=job, attempt_id=attempt_id, event_type=event_type)
        self._session.flush()
        return True

    def retryable_failure(
        self,
        *,
        job_id: UUID,
        attempt_id: UUID,
        error: object,
        now: datetime,
        error_code: str = "retryable_failure",
    ) -> bool:
        job = self._lock_current(job_id=job_id, attempt_id=attempt_id)
        if job is None:
            return False
        definition = self._registry.get(job.job_type, job.handler_version)
        message = str(definition.redact_error(error))
        job.retry_count += 1
        job.last_error = message
        job.last_error_code = error_code
        job.last_error_message = message
        if job.retry_count <= job.max_retries:
            delay = retry_delay_seconds(
                definition.retry_policy,
                job.retry_count - 1,
                random_value=self._random_source(),
            )
            job.status = "queued"
            job.run_after = now + timedelta(seconds=delay)
            job.finished_at = None
            attempt_status = "retryable_failed"
            event_type = "retry_scheduled"
        else:
            job.status = "dead_letter"
            job.finished_at = now
            attempt_status = "dead_letter"
            event_type = "dead_lettered"
        self._finish_attempt(
            job=job,
            attempt_id=attempt_id,
            attempt_status=attempt_status,
            now=now,
            error_code=error_code,
            error_message=message,
        )
        self._event(
            job=job,
            attempt_id=attempt_id,
            event_type=event_type,
            message=message,
        )
        self._session.flush()
        return True

    def block(
        self,
        *,
        job_id: UUID,
        attempt_id: UUID,
        reason: object,
        now: datetime,
        error_code: str = "job_blocked",
    ) -> bool:
        return self._terminal_failure(
            job_id=job_id,
            attempt_id=attempt_id,
            reason=reason,
            now=now,
            job_status="blocked",
            attempt_status="blocked",
            event_type="blocked",
            error_code=error_code,
            terminal=False,
        )

    def dead_letter(
        self,
        *,
        job_id: UUID,
        attempt_id: UUID,
        reason: object,
        now: datetime,
        error_code: str = "permanent_failure",
    ) -> bool:
        return self._terminal_failure(
            job_id=job_id,
            attempt_id=attempt_id,
            reason=reason,
            now=now,
            job_status="dead_letter",
            attempt_status="dead_letter",
            event_type="dead_lettered",
            error_code=error_code,
            terminal=True,
        )

    def confirm_cancelled(
        self,
        *,
        job_id: UUID,
        attempt_id: UUID,
        now: datetime,
    ) -> bool:
        job = self._lock_current(job_id=job_id, attempt_id=attempt_id)
        if job is None or job.cancellation_requested_at is None:
            return False
        job.status = "cancelled"
        job.finished_at = now
        self._finish_attempt(
            job=job,
            attempt_id=attempt_id,
            attempt_status="cancelled",
            now=now,
        )
        self._event(job=job, attempt_id=attempt_id, event_type="cancelled")
        self._session.flush()
        return True

    def _terminal_failure(
        self,
        *,
        job_id: UUID,
        attempt_id: UUID,
        reason: object,
        now: datetime,
        job_status: str,
        attempt_status: str,
        event_type: str,
        error_code: str,
        terminal: bool,
    ) -> bool:
        job = self._lock_current(job_id=job_id, attempt_id=attempt_id)
        if job is None:
            return False
        definition = self._registry.get(job.job_type, job.handler_version)
        message = str(definition.redact_error(reason))
        job.status = job_status
        job.finished_at = now if terminal else None
        job.last_error = message
        job.last_error_code = error_code
        job.last_error_message = message
        self._finish_attempt(
            job=job,
            attempt_id=attempt_id,
            attempt_status=attempt_status,
            now=now,
            error_code=error_code,
            error_message=message,
        )
        self._event(
            job=job,
            attempt_id=attempt_id,
            event_type=event_type,
            message=message,
        )
        self._session.flush()
        return True

    def _lock_current(self, *, job_id: UUID, attempt_id: UUID) -> Job | None:
        return self._session.scalars(
            select(Job)
            .where(
                Job.id == job_id,
                Job.status == "running",
                Job.current_attempt_id == attempt_id,
            )
            .with_for_update()
        ).one_or_none()

    def _finish_attempt(
        self,
        *,
        job: Job,
        attempt_id: UUID,
        attempt_status: str,
        now: datetime,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        attempt = self._session.get(JobAttempt, attempt_id)
        if attempt is None or attempt.status != "running":
            raise ValueError("Current running attempt is missing")
        attempt.status = attempt_status
        attempt.finished_at = now
        attempt.error_code = error_code
        attempt.error_message = error_message
        job.current_attempt_id = None
        job.locked_by = None
        job.locked_until = None
        job.version += 1

    def _event(
        self,
        *,
        job: Job,
        attempt_id: UUID,
        event_type: str,
        message: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        self._session.add(
            JobEvent(
                scope=job.scope,
                workspace_id=job.workspace_id,
                job_id=job.id,
                attempt_id=attempt_id,
                event_type=event_type,
                message=message,
                extra_metadata=dict(metadata) if metadata is not None else None,
            )
        )


__all__ = ["JobTransitions", "transition_target"]
