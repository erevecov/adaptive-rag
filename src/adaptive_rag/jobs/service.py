"""Application service for transactional enqueue and safe job inspection."""

from __future__ import annotations

import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Job, JobAttempt, JobEvent
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.repositories.jobs import JobRepository
from adaptive_rag.jobs.errors import (
    JobCursorError,
    JobIdempotencyConflictError,
    JobNotFoundError,
    JobQueueNotFoundError,
    JobStateConflictError,
    UnknownJobHandlerError,
)
from adaptive_rag.jobs.registry import JobRegistry
from adaptive_rag.jobs.types import (
    JobScope,
    canonical_json_bytes,
    redact_secret_keys,
)


@dataclass(frozen=True, slots=True)
class EnqueueJobRequest:
    scope: JobScope
    workspace_id: UUID | None
    job_type: str
    payload: Mapping[str, object] = field(default_factory=dict)
    handler_version: int = 1
    queue_name: str | None = None
    priority: int | None = None
    idempotency_key: str | None = None
    run_after: datetime | None = None
    schedule_id: UUID | None = None
    scheduled_for: datetime | None = None
    concurrency_key: str | None = None

    @classmethod
    def workspace(
        cls,
        *,
        workspace_id: UUID,
        job_type: str,
        payload: Mapping[str, object] | None = None,
        **options: Any,
    ) -> EnqueueJobRequest:
        return cls(
            scope="workspace",
            workspace_id=workspace_id,
            job_type=job_type,
            payload=payload or {},
            **options,
        )

    @classmethod
    def system(
        cls,
        *,
        job_type: str,
        payload: Mapping[str, object] | None = None,
        **options: Any,
    ) -> EnqueueJobRequest:
        return cls(
            scope="system",
            workspace_id=None,
            job_type=job_type,
            payload=payload or {},
            **options,
        )


@dataclass(frozen=True, slots=True)
class EnqueueJobResult:
    job: Job
    created: bool


@dataclass(frozen=True, slots=True)
class JobActor:
    actor_type: str
    actor_id: str

    def __post_init__(self) -> None:
        if not self.actor_type or len(self.actor_type.encode("utf-8")) > 32:
            raise ValueError("actor_type must be 1-32 UTF-8 bytes")
        if not self.actor_id or len(self.actor_id.encode("utf-8")) > 255:
            raise ValueError("actor_id must be 1-255 UTF-8 bytes")


@dataclass(frozen=True, slots=True)
class JobSnapshot:
    id: UUID
    scope: str
    workspace_id: UUID | None
    queue_name: str
    job_type: str
    handler_version: int
    status: str
    priority: int
    payload_json: object
    result_json: object
    idempotency_key: str | None
    run_after: datetime
    attempt_count: int
    retry_count: int
    max_retries: int
    current_attempt_id: UUID | None
    schedule_id: UUID | None
    scheduled_for: datetime | None
    concurrency_key: str | None
    cancellation_requested_at: datetime | None
    last_error_code: str | None
    last_error_message: str | None
    last_trace_id: str | None
    finished_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class JobPage:
    items: tuple[JobSnapshot, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class JobDetail:
    job: JobSnapshot
    attempts: tuple[JobAttempt, ...]
    events: tuple[JobEvent, ...]


class JobService:
    """Coordinates registry validation with caller-owned SQL transactions."""

    def __init__(self, *, session: Session, registry: JobRegistry) -> None:
        self._session = session
        self._registry = registry
        self._repository = JobRepository(session)

    def enqueue(self, request: EnqueueJobRequest) -> EnqueueJobResult:
        self._validate_scope(request)
        definition = self._registry.get(request.job_type, request.handler_version)
        if request.scope not in definition.allowed_scopes:
            raise ValueError(
                f"Handler {request.job_type}@{request.handler_version} "
                f"does not allow {request.scope} scope"
            )
        payload_model = self._registry.validate_payload(
            request.job_type, request.handler_version, request.payload
        )
        payload = payload_model.model_dump(mode="json")
        queue_name = request.queue_name or definition.queue_name
        if self._repository.get_queue(queue_name) is None:
            raise JobQueueNotFoundError(f"Unknown job queue: {queue_name}")
        priority = (
            definition.default_priority
            if request.priority is None
            else request.priority
        )
        if not -1000 <= priority <= 1000:
            raise ValueError("Job priority must be within [-1000, 1000]")
        self._validate_optional_time(request.run_after, field_name="run_after")
        self._validate_optional_time(request.scheduled_for, field_name="scheduled_for")
        self._validate_key(request.idempotency_key, field_name="idempotency_key")
        concurrency_key = request.concurrency_key
        if concurrency_key is None and definition.concurrency_key is not None:
            concurrency_key = definition.concurrency_key(payload_model)
        self._validate_key(concurrency_key, field_name="concurrency_key")
        if request.scheduled_for is not None and request.schedule_id is None:
            raise ValueError("scheduled_for requires schedule_id")

        fingerprint = None
        if request.idempotency_key is not None:
            fingerprint = self._fingerprint(
                request=request,
                payload=payload,
                queue_name=queue_name,
                priority=priority,
                concurrency_key=concurrency_key,
            )
        job, created = self._repository.enqueue_validated(
            scope=request.scope,
            workspace_id=request.workspace_id,
            queue_name=queue_name,
            job_type=request.job_type,
            handler_version=request.handler_version,
            payload_json=payload,
            priority=priority,
            max_retries=definition.retry_policy.max_retries,
            run_after=request.run_after or utc_now(),
            idempotency_key=request.idempotency_key,
            idempotency_fingerprint=fingerprint,
            schedule_id=request.schedule_id,
            scheduled_for=request.scheduled_for,
            concurrency_key=concurrency_key,
        )
        return EnqueueJobResult(job=job, created=created)

    def list_jobs(
        self,
        *,
        scope: JobScope,
        workspace_id: UUID | None,
        limit: int = 50,
        cursor: str | None = None,
        status: str | None = None,
        queue_name: str | None = None,
        job_type: str | None = None,
        schedule_id: UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> JobPage:
        self._validate_scope_values(scope=scope, workspace_id=workspace_id)
        if not 1 <= limit <= 200:
            raise ValueError("limit must be within [1, 200]")
        decoded_cursor = self._decode_cursor(cursor) if cursor is not None else None
        rows = self._repository.list_page(
            scope=scope,
            workspace_id=workspace_id,
            limit=limit + 1,
            cursor=decoded_cursor,
            status=status,
            queue_name=queue_name,
            job_type=job_type,
            schedule_id=schedule_id,
            created_from=created_from,
            created_to=created_to,
        )
        has_more = len(rows) > limit
        visible = rows[:limit]
        next_cursor = self._encode_cursor(visible[-1]) if has_more else None
        return JobPage(
            items=tuple(self._snapshot(job) for job in visible),
            next_cursor=next_cursor,
        )

    def get_detail(
        self,
        *,
        scope: JobScope,
        workspace_id: UUID | None,
        job_id: UUID,
        history_limit: int = 100,
    ) -> JobDetail:
        self._validate_scope_values(scope=scope, workspace_id=workspace_id)
        if not 1 <= history_limit <= 200:
            raise ValueError("history_limit must be within [1, 200]")
        job = self._repository.get_scoped(
            scope=scope, workspace_id=workspace_id, job_id=job_id
        )
        if job is None:
            raise JobNotFoundError(f"Job not found: {job_id}")
        return JobDetail(
            job=self._snapshot(job),
            attempts=tuple(
                self._repository.list_attempts(job_id=job.id, limit=history_limit)
            ),
            events=tuple(
                self._repository.list_events_bounded(job_id=job.id, limit=history_limit)
            ),
        )

    def cancel(
        self,
        *,
        scope: JobScope,
        workspace_id: UUID | None,
        job_id: UUID,
        actor: JobActor,
        expected_version: int | None = None,
        now: datetime | None = None,
    ) -> JobSnapshot:
        job = self._mutable_job(
            scope=scope,
            workspace_id=workspace_id,
            job_id=job_id,
        )
        if job.status not in {"queued", "blocked", "running"}:
            raise JobStateConflictError(f"Cannot cancel a {job.status} job")
        operation_time = now or utc_now()
        version = job.version if expected_version is None else expected_version
        values: dict[str, object] = {
            "cancellation_requested_at": operation_time,
            "cancellation_requested_by_actor_type": actor.actor_type,
            "cancellation_requested_by_actor_id": actor.actor_id,
            "version": Job.version + 1,
            "updated_at": operation_time,
        }
        event_type = "cancel_requested"
        if job.status in {"queued", "blocked"}:
            values.update(
                status="cancelled",
                finished_at=operation_time,
                current_attempt_id=None,
                locked_by=None,
                locked_until=None,
            )
            event_type = "cancelled"
        self._optimistic_update(
            job=job,
            expected_version=version,
            expected_status=job.status,
            values=values,
        )
        self._add_control_event(job=job, event_type=event_type, actor=actor)
        self._session.flush()
        return self._snapshot(job)

    def retry(
        self,
        *,
        scope: JobScope,
        workspace_id: UUID | None,
        job_id: UUID,
        actor: JobActor,
        expected_version: int | None = None,
        reset_retry_count: bool = False,
        now: datetime | None = None,
    ) -> JobSnapshot:
        return self._requeue_control(
            scope=scope,
            workspace_id=workspace_id,
            job_id=job_id,
            actor=actor,
            expected_version=expected_version,
            expected_status="dead_letter",
            event_type="retried",
            reset_retry_count=reset_retry_count,
            now=now,
        )

    def unblock(
        self,
        *,
        scope: JobScope,
        workspace_id: UUID | None,
        job_id: UUID,
        actor: JobActor,
        expected_version: int | None = None,
        now: datetime | None = None,
    ) -> JobSnapshot:
        return self._requeue_control(
            scope=scope,
            workspace_id=workspace_id,
            job_id=job_id,
            actor=actor,
            expected_version=expected_version,
            expected_status="blocked",
            event_type="unblocked",
            reset_retry_count=False,
            now=now,
        )

    def _snapshot(self, job: Job) -> JobSnapshot:
        try:
            definition = self._registry.get(job.job_type, job.handler_version)
        except UnknownJobHandlerError:
            redact_payload: Callable[[object], object] = redact_secret_keys
            redact_result: Callable[[object], object] = redact_secret_keys
        else:
            redact_payload = definition.redact_payload
            redact_result = definition.redact_result
        return JobSnapshot(
            id=job.id,
            scope=job.scope,
            workspace_id=job.workspace_id,
            queue_name=job.queue_name,
            job_type=job.job_type,
            handler_version=job.handler_version,
            status=job.status,
            priority=job.priority,
            payload_json=redact_payload(job.payload_json),
            result_json=(
                None if job.result_json is None else redact_result(job.result_json)
            ),
            idempotency_key=job.idempotency_key,
            run_after=job.run_after,
            attempt_count=job.attempt_count,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
            current_attempt_id=job.current_attempt_id,
            schedule_id=job.schedule_id,
            scheduled_for=job.scheduled_for,
            concurrency_key=job.concurrency_key,
            cancellation_requested_at=job.cancellation_requested_at,
            last_error_code=job.last_error_code,
            last_error_message=job.last_error_message,
            last_trace_id=job.last_trace_id,
            finished_at=job.finished_at,
            version=job.version,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    def _requeue_control(
        self,
        *,
        scope: JobScope,
        workspace_id: UUID | None,
        job_id: UUID,
        actor: JobActor,
        expected_version: int | None,
        expected_status: str,
        event_type: str,
        reset_retry_count: bool,
        now: datetime | None,
    ) -> JobSnapshot:
        job = self._mutable_job(
            scope=scope,
            workspace_id=workspace_id,
            job_id=job_id,
        )
        if job.status != expected_status:
            raise JobStateConflictError(f"Cannot {event_type} a {job.status} job")
        operation_time = now or utc_now()
        version = job.version if expected_version is None else expected_version
        values: dict[str, object] = {
            "status": "queued",
            "run_after": operation_time,
            "finished_at": None,
            "current_attempt_id": None,
            "locked_by": None,
            "locked_until": None,
            "last_error": None,
            "last_error_code": None,
            "last_error_message": None,
            "cancellation_requested_at": None,
            "cancellation_requested_by_actor_type": None,
            "cancellation_requested_by_actor_id": None,
            "version": Job.version + 1,
            "updated_at": operation_time,
        }
        if reset_retry_count:
            values["retry_count"] = 0
        self._optimistic_update(
            job=job,
            expected_version=version,
            expected_status=expected_status,
            values=values,
        )
        self._add_control_event(job=job, event_type=event_type, actor=actor)
        self._session.flush()
        return self._snapshot(job)

    def _mutable_job(
        self,
        *,
        scope: JobScope,
        workspace_id: UUID | None,
        job_id: UUID,
    ) -> Job:
        self._validate_scope_values(scope=scope, workspace_id=workspace_id)
        job = self._repository.get_scoped(
            scope=scope,
            workspace_id=workspace_id,
            job_id=job_id,
        )
        if job is None:
            raise JobNotFoundError(f"Job not found: {job_id}")
        return job

    def _optimistic_update(
        self,
        *,
        job: Job,
        expected_version: int,
        expected_status: str,
        values: Mapping[str, object],
    ) -> None:
        updated = self._session.execute(
            update(Job)
            .where(
                Job.id == job.id,
                Job.version == expected_version,
                Job.status == expected_status,
            )
            .values(**values)
            .returning(Job.id)
        ).scalar_one_or_none()
        if updated is None:
            raise JobStateConflictError("Job state or version changed")
        self._session.refresh(job)

    def _add_control_event(
        self,
        *,
        job: Job,
        event_type: str,
        actor: JobActor,
    ) -> None:
        self._session.add(
            JobEvent(
                scope=job.scope,
                workspace_id=job.workspace_id,
                job_id=job.id,
                event_type=event_type,
                actor_type=actor.actor_type,
                actor_id=actor.actor_id,
            )
        )

    @staticmethod
    def _validate_scope(request: EnqueueJobRequest) -> None:
        JobService._validate_scope_values(
            scope=request.scope, workspace_id=request.workspace_id
        )

    @staticmethod
    def _validate_scope_values(*, scope: JobScope, workspace_id: UUID | None) -> None:
        if scope == "workspace" and workspace_id is None:
            raise ValueError("workspace scope requires workspace_id")
        if scope == "system" and workspace_id is not None:
            raise ValueError("system scope cannot have workspace_id")

    @staticmethod
    def _validate_optional_time(value: datetime | None, *, field_name: str) -> None:
        if value is not None and value.tzinfo is None:
            raise ValueError(f"{field_name} must be timezone-aware")

    @staticmethod
    def _validate_key(value: str | None, *, field_name: str) -> None:
        if value is None:
            return
        size = len(value.encode("utf-8"))
        if not 1 <= size <= 255:
            raise ValueError(f"{field_name} must be 1-255 UTF-8 bytes")

    @staticmethod
    def _fingerprint(
        *,
        request: EnqueueJobRequest,
        payload: Mapping[str, object],
        queue_name: str,
        priority: int,
        concurrency_key: str | None,
    ) -> str:
        document = {
            "scope": request.scope,
            "workspace_id": (
                None if request.workspace_id is None else str(request.workspace_id)
            ),
            "job_type": request.job_type,
            "handler_version": request.handler_version,
            "payload": payload,
            "queue_name": queue_name,
            "priority": priority,
            "requested_run_after": JobService._canonical_time(request.run_after),
            "schedule_id": (
                None if request.schedule_id is None else str(request.schedule_id)
            ),
            "scheduled_for": JobService._canonical_time(request.scheduled_for),
            "concurrency_key": concurrency_key,
        }
        return sha256(canonical_json_bytes(document)).hexdigest()

    @staticmethod
    def _canonical_time(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.astimezone(UTC).isoformat()

    @staticmethod
    def _encode_cursor(job: Job) -> str:
        payload = json.dumps(
            [job.created_at.isoformat(), str(job.id)], separators=(",", ":")
        ).encode("utf-8")
        return urlsafe_b64encode(payload).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
        try:
            padding = "=" * (-len(cursor) % 4)
            decoded = urlsafe_b64decode(cursor + padding)
            timestamp_raw, job_id_raw = json.loads(decoded)
            timestamp = datetime.fromisoformat(timestamp_raw)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)
            return timestamp, UUID(job_id_raw)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise JobCursorError("Invalid job cursor") from exc


__all__ = [
    "EnqueueJobRequest",
    "EnqueueJobResult",
    "JobActor",
    "JobDetail",
    "JobIdempotencyConflictError",
    "JobPage",
    "JobQueueNotFoundError",
    "JobService",
    "JobSnapshot",
]
