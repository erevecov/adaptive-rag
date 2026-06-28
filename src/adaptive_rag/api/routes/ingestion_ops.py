"""Rutas HTTP de ingestion ops y estado de jobs."""

from __future__ import annotations

import socket
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from adaptive_rag import ingestion_ops
from adaptive_rag.api.dependencies import get_project_contributor_access, get_session
from adaptive_rag.api.schemas.ingestion_ops import (
    EnqueueIngestionJobRequestBody,
    IngestionRunResponse,
    JobDetailResponse,
    JobListResponse,
    JobResponse,
    RetryIngestionJobRequestBody,
    RunNextIngestionJobRequestBody,
)
from adaptive_rag.db.models import Project

router = APIRouter(tags=["ingestion-ops"])


@router.post(
    "/projects/{project_id}/sources/{source_id}/ingestion-jobs",
    response_model=JobResponse,
)
def enqueue_source_ingestion(
    project_id: UUID,
    source_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[
        tuple[Project, str],
        Depends(get_project_contributor_access),
    ],
    body: Annotated[EnqueueIngestionJobRequestBody | None, Body()] = None,
) -> JobResponse:
    active_body = body or EnqueueIngestionJobRequestBody()
    try:
        job = ingestion_ops.enqueue_source_ingestion(
            session,
            project_id=project_id,
            source_id=source_id,
            priority=active_body.priority,
            max_attempts=active_body.max_attempts,
        )
    except ingestion_ops.IngestionOpsError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return JobResponse.from_job(job)


@router.get("/projects/{project_id}/ingestion-jobs", response_model=JobListResponse)
def list_ingestion_jobs(
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[
        tuple[Project, str],
        Depends(get_project_contributor_access),
    ],
    source_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    job_type: Annotated[str | None, Query()] = None,
) -> JobListResponse:
    try:
        jobs = ingestion_ops.list_ingestion_jobs(
            session,
            project_id=project_id,
            source_id=source_id,
            status=status,
            job_type=job_type,
        )
    except ingestion_ops.IngestionOpsError as exc:
        raise _http_error(exc) from exc
    return JobListResponse.from_jobs(jobs)


@router.post(
    "/projects/{project_id}/ingestion-jobs/run-next",
    response_model=IngestionRunResponse,
)
def run_next_ingestion_job(
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[
        tuple[Project, str],
        Depends(get_project_contributor_access),
    ],
    body: Annotated[RunNextIngestionJobRequestBody | None, Body()] = None,
) -> IngestionRunResponse:
    active_body = body or RunNextIngestionJobRequestBody()
    worker_id = active_body.worker_id or _default_worker_id()
    try:
        report = ingestion_ops.run_next_ingestion_job(
            session,
            project_id=project_id,
            worker_id=worker_id,
            lease_seconds=active_body.lease_seconds,
        )
    except ingestion_ops.IngestionOpsError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return IngestionRunResponse.from_report(report)


@router.get(
    "/projects/{project_id}/ingestion-jobs/{job_id}",
    response_model=JobDetailResponse,
)
def get_ingestion_job(
    project_id: UUID,
    job_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[
        tuple[Project, str],
        Depends(get_project_contributor_access),
    ],
) -> JobDetailResponse:
    try:
        detail = ingestion_ops.get_ingestion_job_detail(
            session,
            project_id=project_id,
            job_id=job_id,
        )
    except ingestion_ops.IngestionOpsError as exc:
        raise _http_error(exc) from exc
    return JobDetailResponse.from_job_and_events(
        job=detail.job,
        events=list(detail.events),
    )


@router.post(
    "/projects/{project_id}/ingestion-jobs/{job_id}/retry",
    response_model=JobResponse,
)
def retry_ingestion_job(
    project_id: UUID,
    job_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[
        tuple[Project, str],
        Depends(get_project_contributor_access),
    ],
    body: Annotated[RetryIngestionJobRequestBody | None, Body()] = None,
) -> JobResponse:
    active_body = body or RetryIngestionJobRequestBody()
    try:
        job = ingestion_ops.retry_ingestion_job(
            session,
            project_id=project_id,
            job_id=job_id,
            reset_attempts=active_body.reset_attempts,
        )
    except ingestion_ops.IngestionOpsError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return JobResponse.from_job(job)


def _http_error(error: ingestion_ops.IngestionOpsError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.detail)


def _default_worker_id() -> str:
    return f"api-{socket.gethostname()}"
