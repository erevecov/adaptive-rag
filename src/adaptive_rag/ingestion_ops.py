"""Operaciones publicas de ingestion y estado de jobs."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag import authoring
from adaptive_rag.contextualization import Contextualizer
from adaptive_rag.db.models import Job, JobEvent
from adaptive_rag.db.repositories import JobRepository
from adaptive_rag.embeddings import DenseEmbeddingProvider, SparseEmbeddingProvider
from adaptive_rag.ingestion.indexing import (
    INDEX_DOCUMENT_VERSION_JOB_TYPE,
    IndexingBlockedResult,
    IndexingPipeline,
    IndexingRunResult,
)
from adaptive_rag.ingestion.pipeline import (
    INGEST_SOURCE_JOB_TYPE,
    INGESTION_FAMILY_JOB_TYPES,
    IngestionBlockedResult,
    IngestionPipeline,
    IngestionRunResult,
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
    job_type: str | None = None
    source_id: UUID | None = None
    document_id: UUID | None = None
    document_version_id: UUID | None = None
    created_document_version: bool | None = None
    chunk_count: int | None = None
    contextualized_chunk_count: int | None = None
    reused_contextualized_chunk_count: int | None = None
    embedded_chunk_count: int | None = None
    reused_chunk_count: int | None = None
    sparse_embedded_chunk_count: int | None = None
    sparse_reused_chunk_count: int | None = None
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
    dense_embedding_provider: DenseEmbeddingProvider | None = None,
    sparse_embedding_provider: SparseEmbeddingProvider | None = None,
    contextualizer: Contextualizer | None = None,
) -> IngestionRunReport:
    _ensure_project_exists(session=session, project_id=project_id)
    active_now = now or datetime.now(UTC)
    lease_until = active_now + timedelta(seconds=lease_seconds)
    job_repo = JobRepository(session)
    # Recover kill-mid-job / crashed workers before selecting new work.
    job_repo.release_expired_leases(project_id=project_id, now=active_now)
    job = job_repo.lease_next(
        project_id=project_id,
        worker_id=worker_id,
        now=active_now,
        lease_until=lease_until,
        job_types=tuple(sorted(INGESTION_FAMILY_JOB_TYPES)),
    )
    if job is None:
        return IngestionRunReport(
            status="idle",
            project_id=project_id,
            worker_id=worker_id,
        )

    # Snapshot lease-time values: after a mid-pipeline flush failure the
    # session is poisoned and ORM attribute access can itself raise.
    job_id = job.id
    attempts_at_lease = job.attempts

    try:
        if job.job_type == INGEST_SOURCE_JOB_TYPE:
            ingest_result = IngestionPipeline(session).process_leased_job(
                project_id=project_id,
                job=job,
            )
            return _report_from_ingest_result(
                project_id=project_id,
                worker_id=worker_id,
                result=ingest_result,
            )

        if job.job_type == INDEX_DOCUMENT_VERSION_JOB_TYPE:
            index_result = IndexingPipeline(
                session,
                dense_embedding_provider=dense_embedding_provider,
                sparse_embedding_provider=sparse_embedding_provider,
                contextualizer=contextualizer,
            ).process_leased_job(
                project_id=project_id,
                job=job,
            )
            return _report_from_index_result(
                project_id=project_id,
                worker_id=worker_id,
                result=index_result,
            )
    except Exception as exc:  # noqa: BLE001 — unexpected worker failures
        backoff = _retry_backoff_seconds(attempts_at_lease)
        error_message = str(exc) or exc.__class__.__name__
        try:
            failed = job_repo.fail(
                project_id=project_id,
                job_id=job_id,
                error_message=error_message,
                retry_after=active_now + timedelta(seconds=backoff),
                worker_id=worker_id,
            )
        except Exception:  # noqa: BLE001 — session poisoned by a failed flush
            # A mid-pipeline flush failure leaves the session unable to run
            # more statements; roll back and record the failure so the job is
            # requeued/dead-lettered instead of leaking past the handler.
            session.rollback()
            failed = job_repo.fail(
                project_id=project_id,
                job_id=job_id,
                error_message=error_message,
                retry_after=active_now + timedelta(seconds=backoff),
                worker_id=worker_id,
            )
        return IngestionRunReport(
            status="failed" if failed.status == "queued" else "dead_letter",
            project_id=project_id,
            worker_id=worker_id,
            job_id=failed.id,
            job_type=failed.job_type,
            source_id=_job_source_id(failed),
            document_version_id=_job_document_version_id(failed),
            error_message=failed.last_error,
        )

    blocked = job_repo.block(
        project_id=project_id,
        job_id=job.id,
        reason=f"unsupported ingestion-family job_type: {job.job_type}",
        worker_id=worker_id,
    )
    return IngestionRunReport(
        status="blocked",
        project_id=project_id,
        worker_id=worker_id,
        job_id=blocked.id,
        job_type=blocked.job_type,
        source_id=_job_source_id(blocked),
        error_message=blocked.last_error,
    )


def _retry_backoff_seconds(attempts: int) -> int:
    """Deterministic exponential backoff capped at 60s."""

    safe_attempts = max(1, attempts)
    return min(60, int(2 ** (safe_attempts - 1)))


def run_ingestion_family_until_idle(
    session: Session,
    *,
    project_id: UUID,
    worker_id: str,
    lease_seconds: int = 300,
    max_jobs: int = 32,
    dense_embedding_provider: DenseEmbeddingProvider | None = None,
    sparse_embedding_provider: SparseEmbeddingProvider | None = None,
    contextualizer: Contextualizer | None = None,
) -> list[IngestionRunReport]:
    """Process ready ingest/index jobs until idle or max_jobs."""

    reports: list[IngestionRunReport] = []
    for _ in range(max_jobs):
        report = run_next_ingestion_job(
            session,
            project_id=project_id,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
            dense_embedding_provider=dense_embedding_provider,
            sparse_embedding_provider=sparse_embedding_provider,
            contextualizer=contextualizer,
        )
        if report.status == "idle":
            break
        reports.append(report)
        if report.status == "blocked":
            break
    return reports


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


def _report_from_ingest_result(
    *,
    project_id: UUID,
    worker_id: str,
    result: IngestionRunResult | IngestionBlockedResult,
) -> IngestionRunReport:
    if isinstance(result, IngestionBlockedResult):
        return IngestionRunReport(
            status="blocked",
            project_id=project_id,
            worker_id=worker_id,
            job_id=result.job.id,
            job_type=result.job.job_type,
            source_id=_job_source_id(result.job),
            error_message=result.error_message,
        )
    return IngestionRunReport(
        status="processed",
        project_id=project_id,
        worker_id=worker_id,
        job_id=result.job.id,
        job_type=result.job.job_type,
        source_id=result.source.id,
        document_id=result.document.id,
        document_version_id=result.document_version.id,
        created_document_version=result.created_document_version,
    )


def _report_from_index_result(
    *,
    project_id: UUID,
    worker_id: str,
    result: IndexingRunResult | IndexingBlockedResult,
) -> IngestionRunReport:
    if isinstance(result, IndexingBlockedResult):
        return IngestionRunReport(
            status="blocked",
            project_id=project_id,
            worker_id=worker_id,
            job_id=result.job.id,
            job_type=result.job.job_type,
            source_id=_job_source_id(result.job),
            document_version_id=_job_document_version_id(result.job),
            error_message=result.error_message,
        )
    return IngestionRunReport(
        status="processed",
        project_id=project_id,
        worker_id=worker_id,
        job_id=result.job.id,
        job_type=result.job.job_type,
        source_id=result.source_id,
        document_version_id=result.document_version.id,
        chunk_count=result.chunk_count,
        contextualized_chunk_count=result.contextualized_chunk_count,
        reused_contextualized_chunk_count=result.reused_contextualized_chunk_count,
        embedded_chunk_count=result.embedded_chunk_count,
        reused_chunk_count=result.reused_chunk_count,
        sparse_embedded_chunk_count=result.sparse_embedded_chunk_count,
        sparse_reused_chunk_count=result.sparse_reused_chunk_count,
    )


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


def _job_document_version_id(job: Job) -> UUID | None:
    payload = job.payload_json or {}
    raw_id = payload.get("document_version_id")
    if not isinstance(raw_id, str):
        return None
    try:
        return UUID(raw_id)
    except ValueError:
        return None
