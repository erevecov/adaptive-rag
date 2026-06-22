"""Comandos CLI para worker de jobs."""

from __future__ import annotations

import json
import os
import socket
import time
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import typer

from adaptive_rag.db.session import session_scope
from adaptive_rag.ingestion.pipeline import IngestionPipeline

app = typer.Typer(no_args_is_help=True)


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
    """Procesa jobs `ingest_source` de un proyecto usando el pipeline local."""

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
    now = datetime.now(UTC)
    lease_until = now + timedelta(seconds=lease_seconds)
    with session_scope() as session:
        result = IngestionPipeline(session).run_next(
            project_id=project_id,
            worker_id=worker_id,
            now=now,
            lease_until=lease_until,
        )
        session.commit()

    if result is None:
        return {
            "status": "idle",
            "project_id": str(project_id),
            "worker_id": worker_id,
            "processed_jobs": processed_jobs,
        }

    return {
        "status": "processed",
        "project_id": str(project_id),
        "worker_id": worker_id,
        "processed_jobs": processed_jobs,
        "job_id": str(result.job.id),
        "source_id": str(result.source.id),
        "document_id": str(result.document.id),
        "document_version_id": str(result.document_version.id),
        "created_document_version": result.created_document_version,
    }


def _default_worker_id() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"
