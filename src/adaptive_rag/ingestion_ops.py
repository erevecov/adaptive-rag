"""Operaciones publicas de ingestion y estado de jobs."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag import authoring
from adaptive_rag.db.models import Job, JobEvent
from adaptive_rag.db.repositories import JobRepository
from adaptive_rag.ingestion.pipeline import (
    INGEST_SOURCE_JOB_TYPE,
    IngestionBlockedResult,
    IngestionPipeline,
)


class IngestionOpsError(Exception):
    """Error esperado de ingestion ops con mensaje estable para API y CLI."""

    def __init__(self, detail: str, *, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class IngestionJobDetail:
    job: Job
    events: Sequence[JobEvent]


@dataclass(frozen=True, slots=True)
class IngestionRunReport:
    status: str
    project_id: UUID
    worker_id: str
    job_id: UUID | None = None
    source_id: UUID | None = None
    document_id: UUID | None = None
    document_version_id: UUID | None = None
    created_document_version: bool | None = None
    error_message: str | None = None


def enqueue_source_ingestion(
    session: Session,
    *,
    project_id: UUID,
    source_id: UUID,
    priority: int = 0,
    max_attempts: int = 3,
    run_after: datetime | None = None,
) -> Job:
    _ensure_project_exists(session=session, project_id=project_id)
    try:
        authoring.get_source(session, project_id=project_id, source_id=source_id)
    except authoring.AuthoringError as exc:
        raise IngestionOpsError(exc.detail, status_code=exc.status_code) from exc

    return JobRepository(session).create(
        project_id=project_id,
        job_type=INGEST_SOURCE_JOB_TYPE,
        payload_json={"source_id": str(source_id)},
        priority=priority,
        max_attempts=max_attempts,
        run_after=run_after,
    )


def list_ingestion_jobs(
    session: Session,
    *,
    project_id: UUID,
    source_id: UUID | None = None,
    status: str | None = None,
    job_type: str | None = None,
) -> list[Job]:
    _ensure_project_exists(session=session, project_id=project_id)
    jobs = JobRepository(session).list(
        project_id=project_id,
        status=status,
        job_type=job_type,
    )
    if source_id is None:
        return jobs
    return [job for job in jobs if _job_source_id(job) == source_id]


def get_ingestion_job_detail(
    session: Session,
    *,
    project_id: UUID,
    job_id: UUID,
) -> IngestionJobDetail:
    _ensure_project_exists(session=session, project_id=project_id)
    job_repository = JobRepository(session)
    job = job_repository.get(project_id=project_id, job_id=job_id)
    if job is None:
        raise IngestionOpsError("job not found", status_code=404)
    return IngestionJobDetail(
        job=job,
        events=job_repository.list_events(project_id=project_id, job_id=job_id),
    )


def retry_ingestion_job(
    session: Session,
    *,
    project_id: UUID,
    job_id: UUID,
    run_after: datetime | None = None,
    reset_attempts: bool = True,
) -> Job:
    _ensure_project_exists(session=session, project_id=project_id)
    job_repository = JobRepository(session)
    if job_repository.get(project_id=project_id, job_id=job_id) is None:
        raise IngestionOpsError("job not found", status_code=404)
    try:
        return job_repository.requeue(
            project_id=project_id,
            job_id=job_id,
            run_after=run_after,
            reset_attempts=reset_attempts,
        )
    except ValueError as exc:
        if str(exc) == "job is not retryable":
            raise IngestionOpsError("job is not retryable", status_code=409) from exc
        raise


def run_next_ingestion_job(
    session: Session,
    *,
    project_id: UUID,
    worker_id: str,
    lease_seconds: int = 300,
    now: datetime | None = None,
) -> IngestionRunReport:
    _ensure_project_exists(session=session, project_id=project_id)
    active_now = now or datetime.now(UTC)
    result = IngestionPipeline(session).run_next(
        project_id=project_id,
        worker_id=worker_id,
        now=active_now,
        lease_until=active_now + timedelta(seconds=lease_seconds),
    )
    if result is None:
        return IngestionRunReport(
            status="idle",
            project_id=project_id,
            worker_id=worker_id,
        )
    if isinstance(result, IngestionBlockedResult):
        return IngestionRunReport(
            status="blocked",
            project_id=project_id,
            worker_id=worker_id,
            job_id=result.job.id,
            source_id=_job_source_id(result.job),
            error_message=result.error_message,
        )
    return IngestionRunReport(
        status="processed",
        project_id=project_id,
        worker_id=worker_id,
        job_id=result.job.id,
        source_id=result.source.id,
        document_id=result.document.id,
        document_version_id=result.document_version.id,
        created_document_version=result.created_document_version,
    )


def job_payload(job: Job) -> dict[str, object]:
    return {
        "id": str(job.id),
        "project_id": str(job.project_id),
        "job_type": job.job_type,
        "status": job.status,
        "priority": job.priority,
        "payload_json": job.payload_json,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "run_after": job.run_after.isoformat(),
        "locked_by": job.locked_by,
        "locked_until": (
            job.locked_until.isoformat() if job.locked_until is not None else None
        ),
        "last_error": job.last_error,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


def job_event_payload(event: JobEvent) -> dict[str, object]:
    return {
        "id": str(event.id),
        "project_id": str(event.project_id),
        "job_id": str(event.job_id),
        "event_type": event.event_type,
        "message": event.message,
        "extra_metadata": event.extra_metadata,
        "created_at": event.created_at.isoformat(),
    }


def _ensure_project_exists(*, session: Session, project_id: UUID) -> None:
    try:
        authoring.get_project(session, project_id)
    except authoring.AuthoringError as exc:
        raise IngestionOpsError(exc.detail, status_code=exc.status_code) from exc


def _job_source_id(job: Job) -> UUID | None:
    payload = job.payload_json or {}
    raw_source_id = payload.get("source_id")
    if not isinstance(raw_source_id, str):
        return None
    try:
        return UUID(raw_source_id)
    except ValueError:
        return None
