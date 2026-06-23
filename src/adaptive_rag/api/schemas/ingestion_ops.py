"""Schemas HTTP para ingestion ops y estado de jobs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from adaptive_rag.db.models import Job, JobEvent
from adaptive_rag.ingestion_ops import IngestionRunReport


class EnqueueIngestionJobRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: int = 0
    max_attempts: int = Field(default=3, ge=1)


class RetryIngestionJobRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reset_attempts: bool = True


class RunNextIngestionJobRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worker_id: str | None = None
    lease_seconds: int = Field(default=300, ge=1)


class JobResponse(BaseModel):
    id: UUID
    project_id: UUID
    job_type: str
    status: str
    priority: int
    payload_json: dict[str, Any] | None
    attempts: int
    max_attempts: int
    run_after: datetime
    locked_by: str | None
    locked_until: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_job(cls, job: Job) -> JobResponse:
        return cls(
            id=job.id,
            project_id=job.project_id,
            job_type=job.job_type,
            status=job.status,
            priority=job.priority,
            payload_json=job.payload_json,
            attempts=job.attempts,
            max_attempts=job.max_attempts,
            run_after=job.run_after,
            locked_by=job.locked_by,
            locked_until=job.locked_until,
            last_error=job.last_error,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )


class JobEventResponse(BaseModel):
    id: UUID
    project_id: UUID
    job_id: UUID
    event_type: str
    message: str | None
    extra_metadata: dict[str, Any] | None
    created_at: datetime

    @classmethod
    def from_event(cls, event: JobEvent) -> JobEventResponse:
        return cls(
            id=event.id,
            project_id=event.project_id,
            job_id=event.job_id,
            event_type=event.event_type,
            message=event.message,
            extra_metadata=event.extra_metadata,
            created_at=event.created_at,
        )


class JobListResponse(BaseModel):
    items: list[JobResponse]

    @classmethod
    def from_jobs(cls, jobs: list[Job]) -> JobListResponse:
        return cls(items=[JobResponse.from_job(job) for job in jobs])


class JobDetailResponse(BaseModel):
    job: JobResponse
    events: list[JobEventResponse]

    @classmethod
    def from_job_and_events(
        cls,
        *,
        job: Job,
        events: list[JobEvent],
    ) -> JobDetailResponse:
        return cls(
            job=JobResponse.from_job(job),
            events=[JobEventResponse.from_event(event) for event in events],
        )


class IngestionRunResponse(BaseModel):
    status: str
    project_id: UUID
    worker_id: str
    job_id: UUID | None
    source_id: UUID | None
    document_id: UUID | None
    document_version_id: UUID | None
    created_document_version: bool | None
    error_message: str | None

    @classmethod
    def from_report(cls, report: IngestionRunReport) -> IngestionRunResponse:
        return cls(
            status=report.status,
            project_id=report.project_id,
            worker_id=report.worker_id,
            job_id=report.job_id,
            source_id=report.source_id,
            document_id=report.document_id,
            document_version_id=report.document_version_id,
            created_document_version=report.created_document_version,
            error_message=report.error_message,
        )
