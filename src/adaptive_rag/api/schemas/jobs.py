"""Bounded HTTP contracts for background jobs and schedules."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from adaptive_rag.jobs.service import JobDetail, JobPage, JobSnapshot
from adaptive_rag.jobs.types import redact_secret_keys


class BackgroundJobResponse(BaseModel):
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
    last_error: dict[str, str | None] | None
    finished_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_snapshot(cls, job: JobSnapshot) -> BackgroundJobResponse:
        error = None
        if job.last_error_code is not None or job.last_error_message is not None:
            error = {
                "code": job.last_error_code,
                "message": job.last_error_message,
                "trace_id": job.last_trace_id,
            }
        return cls(
            id=job.id,
            scope=job.scope,
            workspace_id=job.workspace_id,
            queue_name=job.queue_name,
            job_type=job.job_type,
            handler_version=job.handler_version,
            status=job.status,
            priority=job.priority,
            payload_json=job.payload_json,
            result_json=job.result_json,
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
            last_error=error,
            finished_at=job.finished_at,
            version=job.version,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )


class JobAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    attempt_number: int
    worker_id: UUID
    status: str
    started_at: datetime
    heartbeat_at: datetime
    lease_expires_at: datetime
    finished_at: datetime | None
    progress_json: dict[str, Any] | None
    error_code: str | None
    error_message: str | None
    trace_id: str | None


class JobEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    attempt_id: UUID | None
    event_type: str
    message: str | None
    extra_metadata: dict[str, Any] | None
    actor_type: str | None
    actor_id: str | None
    created_at: datetime


class JobDetailResponse(BaseModel):
    job: BackgroundJobResponse
    attempts: list[JobAttemptResponse]
    events: list[JobEventResponse]

    @classmethod
    def from_detail(cls, detail: JobDetail) -> JobDetailResponse:
        return cls(
            job=BackgroundJobResponse.from_snapshot(detail.job),
            attempts=[
                JobAttemptResponse.model_validate(row) for row in detail.attempts
            ],
            events=[
                JobEventResponse.model_validate(row).model_copy(
                    update={
                        "extra_metadata": (
                            None
                            if row.extra_metadata is None
                            else redact_secret_keys(row.extra_metadata)
                        )
                    }
                )
                for row in detail.events
            ],
        )


class JobPageResponse(BaseModel):
    items: list[BackgroundJobResponse]
    next_cursor: str | None

    @classmethod
    def from_page(cls, page: JobPage) -> JobPageResponse:
        return cls(
            items=[BackgroundJobResponse.from_snapshot(row) for row in page.items],
            next_cursor=page.next_cursor,
        )


class EnqueueJobBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_type: str = Field(min_length=1, max_length=100)
    handler_version: int = Field(default=1, ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    queue_name: str | None = Field(default=None, min_length=1, max_length=100)
    priority: int | None = Field(default=None, ge=-1000, le=1000)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=255)
    run_after: datetime | None = None
    concurrency_key: str | None = Field(default=None, min_length=1, max_length=255)


class EnqueueJobResponse(BaseModel):
    created: bool
    job: BackgroundJobResponse


class VersionMutationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    reset_retry_count: bool = False


class JobHandlerResponse(BaseModel):
    name: str
    version: int
    queue_name: str
    allowed_scopes: list[str]
    allow_manual_enqueue: bool
    minimum_manual_role: str


class CreateJobScheduleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    job_type: str = Field(min_length=1, max_length=100)
    handler_version: int = Field(default=1, ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    queue_name: str | None = Field(default=None, min_length=1, max_length=100)
    priority: int | None = Field(default=None, ge=-1000, le=1000)
    concurrency_key: str | None = Field(default=None, min_length=1, max_length=255)
    cron_expression: str = Field(min_length=1, max_length=255)
    timezone: str = Field(min_length=1, max_length=100)
    misfire_policy: Literal["skip", "run_once", "catch_up"] = "run_once"
    max_catch_up: int = Field(default=1, ge=1, le=100)


class JobScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scope: str
    workspace_id: UUID | None
    name: str
    description: str | None
    queue_name: str
    job_type: str
    handler_version: int
    payload_json: dict[str, Any]
    priority: int
    concurrency_key: str | None
    cron_expression: str
    timezone: str
    misfire_policy: str
    max_catch_up: int
    paused_at: datetime | None
    archived_at: datetime | None
    next_run_at: datetime
    last_scheduled_for: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime


class UpdateJobScheduleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    payload: dict[str, Any] | None = None
    queue_name: str | None = Field(default=None, min_length=1, max_length=100)
    priority: int | None = Field(default=None, ge=-1000, le=1000)
    concurrency_key: str | None = Field(default=None, min_length=1, max_length=255)
    cron_expression: str | None = Field(default=None, min_length=1, max_length=255)
    timezone: str | None = Field(default=None, min_length=1, max_length=100)
    misfire_policy: Literal["skip", "run_once", "catch_up"] | None = None
    max_catch_up: int | None = Field(default=None, ge=1, le=100)


class JobScheduleListResponse(BaseModel):
    items: list[JobScheduleResponse]


class JobQueueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    paused_at: datetime | None
    global_concurrency_limit: int | None
    workspace_concurrency_limit: int | None
    default_lease_seconds: int
    version: int


class ConfigureJobQueueBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    paused: bool | None = None
    global_concurrency_limit: int | None = Field(default=None, ge=1)
    workspace_concurrency_limit: int | None = Field(default=None, ge=1)
    default_lease_seconds: int | None = Field(default=None, ge=15, le=3600)


class JobWorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    process_identity: str
    application_version: str
    supported_queues: list[str]
    supported_handlers: list[str]
    max_concurrency: int
    started_at: datetime
    heartbeat_at: datetime
    draining_at: datetime | None
    shutdown_at: datetime | None


__all__ = [
    "BackgroundJobResponse",
    "ConfigureJobQueueBody",
    "CreateJobScheduleBody",
    "EnqueueJobBody",
    "EnqueueJobResponse",
    "JobDetailResponse",
    "JobHandlerResponse",
    "JobPageResponse",
    "JobQueueResponse",
    "JobScheduleListResponse",
    "JobScheduleResponse",
    "JobWorkerResponse",
    "UpdateJobScheduleBody",
    "VersionMutationBody",
]
