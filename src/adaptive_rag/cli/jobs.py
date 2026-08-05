"""Comandos CLI para worker de jobs."""

from __future__ import annotations

import json
import os
import socket
import time
from typing import Annotated, NoReturn
from uuid import UUID

import typer

from adaptive_rag import ingestion_ops
from adaptive_rag.db.session import session_scope

app = typer.Typer(no_args_is_help=True)


@app.command("enqueue-ingest-source")
def enqueue_ingest_source(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    source_id: Annotated[UUID, typer.Option("--source-id")],
    priority: Annotated[int, typer.Option("--priority")] = 0,
    max_attempts: Annotated[int, typer.Option("--max-attempts", min=1)] = 3,
) -> None:
    with session_scope() as session:
        try:
            job = ingestion_ops.enqueue_source_ingestion(
                session,
                project_id=project_id,
                source_id=source_id,
                priority=priority,
                max_attempts=max_attempts,
            )
        except ingestion_ops.IngestionOpsError as exc:
            _exit_ingestion_ops_error(exc)
        session.commit()
        payload = ingestion_ops.job_payload(job)

    typer.echo(json.dumps(payload))


@app.command("list")
def list_jobs(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    source_id: Annotated[UUID | None, typer.Option("--source-id")] = None,
    status: Annotated[str | None, typer.Option("--status")] = None,
    job_type: Annotated[str | None, typer.Option("--job-type")] = None,
) -> None:
    with session_scope() as session:
        try:
            jobs = ingestion_ops.list_ingestion_jobs(
                session,
                project_id=project_id,
                source_id=source_id,
                status=status,
                job_type=job_type,
            )
        except ingestion_ops.IngestionOpsError as exc:
            _exit_ingestion_ops_error(exc)
        payload = {"items": [ingestion_ops.job_payload(job) for job in jobs]}

    typer.echo(json.dumps(payload))


@app.command("show")
def show_job(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    job_id: Annotated[UUID, typer.Option("--job-id")],
) -> None:
    with session_scope() as session:
        try:
            detail = ingestion_ops.get_ingestion_job_detail(
                session,
                project_id=project_id,
                job_id=job_id,
            )
        except ingestion_ops.IngestionOpsError as exc:
            _exit_ingestion_ops_error(exc)
        payload = {
            "job": ingestion_ops.job_payload(detail.job),
            "events": [
                ingestion_ops.job_event_payload(event) for event in detail.events
            ],
        }

    typer.echo(json.dumps(payload))


@app.command("retry")
def retry_job(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    job_id: Annotated[UUID, typer.Option("--job-id")],
    reset_attempts: Annotated[bool, typer.Option("--reset-attempts")] = True,
) -> None:
    with session_scope() as session:
        try:
            job = ingestion_ops.retry_ingestion_job(
                session,
                project_id=project_id,
                job_id=job_id,
                reset_attempts=reset_attempts,
            )
        except ingestion_ops.IngestionOpsError as exc:
            _exit_ingestion_ops_error(exc)
        session.commit()
        payload = ingestion_ops.job_payload(job)

    typer.echo(json.dumps(payload))


@app.command("run-worker")
def run_worker(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    worker_id: Annotated[str | None, typer.Option("--worker-id")] = None,
    once: Annotated[
        bool,
        typer.Option("--once", help="Process at most one available job and exit."),
    ] = False,
    poll_interval_seconds: Annotated[
        float,
        typer.Option("--poll-interval-seconds", min=0.1),
    ] = 5.0,
    lease_seconds: Annotated[
        int,
        typer.Option("--lease-seconds", min=1),
    ] = 300,
    max_jobs: Annotated[int | None, typer.Option("--max-jobs", min=1)] = None,
) -> None:
    """Procesa jobs `ingest_source` e `index_document_version` del proyecto."""

    active_worker_id = worker_id or _default_worker_id()
    processed_jobs = 0

    while True:
        payload = _run_worker_once(
            project_id=project_id,
            worker_id=active_worker_id,
            lease_seconds=lease_seconds,
            processed_jobs=processed_jobs,
        )
        if payload["status"] == "processed":
            processed_jobs += 1
            payload["processed_jobs"] = processed_jobs

        typer.echo(json.dumps(payload))

        reached_max_jobs = max_jobs is not None and processed_jobs >= max_jobs
        should_exit = once or reached_max_jobs
        if should_exit:
            return
        if payload["status"] == "idle":
            time.sleep(poll_interval_seconds)


def _run_worker_once(
    *,
    project_id: UUID,
    worker_id: str,
    lease_seconds: int,
    processed_jobs: int,
) -> dict[str, object]:
    with session_scope() as session:
        report = ingestion_ops.run_next_ingestion_job(
            session,
            project_id=project_id,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
        )
        session.commit()

    payload: dict[str, object] = {
        "status": report.status,
        "project_id": str(report.project_id),
        "worker_id": report.worker_id,
        "processed_jobs": processed_jobs,
    }
    if report.job_id is not None:
        payload["job_id"] = str(report.job_id)
    if report.job_type is not None:
        payload["job_type"] = report.job_type
    if report.source_id is not None:
        payload["source_id"] = str(report.source_id)
    if report.document_id is not None:
        payload["document_id"] = str(report.document_id)
    if report.document_version_id is not None:
        payload["document_version_id"] = str(report.document_version_id)
    if report.created_document_version is not None:
        payload["created_document_version"] = report.created_document_version
    if report.chunk_count is not None:
        payload["chunk_count"] = report.chunk_count
    if report.embedded_chunk_count is not None:
        payload["embedded_chunk_count"] = report.embedded_chunk_count
    if report.error_message is not None:
        payload["error_message"] = report.error_message
    return payload


def _default_worker_id() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


def _exit_ingestion_ops_error(error: ingestion_ops.IngestionOpsError) -> NoReturn:
    typer.echo(error.detail, err=True)
    raise typer.Exit(1)
