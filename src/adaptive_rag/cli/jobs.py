"""Comandos CLI para worker de jobs."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import time
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Annotated, NoReturn
from uuid import UUID

import typer
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag import ingestion_ops
from adaptive_rag.api.schemas.jobs import (
    BackgroundJobResponse,
    JobDetailResponse,
    JobPageResponse,
    JobQueueResponse,
    JobScheduleResponse,
    JobWorkerResponse,
)
from adaptive_rag.db.session import create_job_session_factory, session_scope
from adaptive_rag.jobs.handlers import build_ingestion_registry
from adaptive_rag.jobs.registry import JobRegistry
from adaptive_rag.jobs.retention import JobRetention, RetentionPolicy
from adaptive_rag.jobs.schedule_service import (
    CreateJobScheduleRequest,
    JobScheduleService,
)
from adaptive_rag.jobs.scheduler import JobScheduler
from adaptive_rag.jobs.service import EnqueueJobRequest, JobActor, JobService
from adaptive_rag.jobs.types import JobScope
from adaptive_rag.jobs.worker import JobWorker

app = typer.Typer(no_args_is_help=True)
schedules_app = typer.Typer(no_args_is_help=True, help="Manage durable job schedules.")
queues_app = typer.Typer(no_args_is_help=True, help="Manage job queues.")
workers_app = typer.Typer(no_args_is_help=True, help="Inspect worker presence.")
app.add_typer(schedules_app, name="schedules")
app.add_typer(queues_app, name="queues")
app.add_typer(workers_app, name="workers")

_CLI_ACTOR = JobActor(actor_type="operator", actor_id="cli")


@app.command("retention")
def run_retention(
    apply: Annotated[bool, typer.Option("--apply")] = False,
    batch_size: Annotated[int, typer.Option("--batch-size", min=1, max=10_000)] = 1_000,
    succeeded_days: Annotated[int, typer.Option("--succeeded-days", min=1)] = 30,
    cancelled_days: Annotated[int, typer.Option("--cancelled-days", min=1)] = 30,
    dead_letter_days: Annotated[
        int, typer.Option("--dead-letter-days", min=1)
    ] = 90,
) -> None:
    """Preview or apply bounded retention for unprotected terminal jobs."""

    factory, _registry = _job_runtime()
    try:
        with factory() as session:
            report = JobRetention(session=session).run(
                policy=RetentionPolicy(
                    succeeded_after=timedelta(days=succeeded_days),
                    cancelled_after=timedelta(days=cancelled_days),
                    dead_letter_after=timedelta(days=dead_letter_days),
                ),
                now=datetime.now(UTC),
                dry_run=not apply,
                batch_size=batch_size,
            )
            if apply:
                session.commit()
            else:
                session.rollback()
    except Exception as exc:  # noqa: BLE001 - stable CLI boundary
        _exit_job_error(exc)
    _echo_json(asdict(report))


@app.command("enqueue")
def enqueue_job(
    job_type: Annotated[str, typer.Option("--job-type")],
    workspace_id: Annotated[UUID | None, typer.Option("--workspace-id")] = None,
    system: Annotated[bool, typer.Option("--system")] = False,
    payload_json: Annotated[str, typer.Option("--payload-json")] = "{}",
    handler_version: Annotated[int, typer.Option("--handler-version", min=1)] = 1,
    queue_name: Annotated[str | None, typer.Option("--queue")] = None,
    priority: Annotated[
        int | None, typer.Option("--priority", min=-1000, max=1000)
    ] = None,
    idempotency_key: Annotated[str | None, typer.Option("--idempotency-key")] = None,
    run_after: Annotated[datetime | None, typer.Option("--run-after")] = None,
    concurrency_key: Annotated[str | None, typer.Option("--concurrency-key")] = None,
) -> None:
    """Enqueue a registered handler after validating its JSON payload."""

    payload = _parse_payload_json(payload_json)
    scope, active_workspace_id = _resolve_scope(
        workspace_id=workspace_id, system=system
    )
    factory, registry = _job_runtime()
    try:
        with factory() as session:
            service = JobService(session=session, registry=registry)
            result = service.enqueue(
                EnqueueJobRequest(
                    scope=scope,
                    workspace_id=active_workspace_id,
                    job_type=job_type,
                    handler_version=handler_version,
                    payload=payload,
                    queue_name=queue_name,
                    priority=priority,
                    idempotency_key=idempotency_key,
                    run_after=run_after,
                    concurrency_key=concurrency_key,
                )
            )
            session.commit()
            response = {
                "created": result.created,
                "job": BackgroundJobResponse.from_snapshot(
                    service.snapshot(result.job)
                ).model_dump(mode="json"),
            }
    except Exception as exc:  # noqa: BLE001 - stable CLI boundary
        _exit_job_error(exc)
    _echo_json(response)


@app.command("cancel")
def cancel_job(
    job_id: Annotated[UUID, typer.Option("--job-id")],
    workspace_id: Annotated[UUID | None, typer.Option("--workspace-id")] = None,
    system: Annotated[bool, typer.Option("--system")] = False,
    version: Annotated[int | None, typer.Option("--version", min=1)] = None,
) -> None:
    _mutate_job(
        operation="cancel",
        job_id=job_id,
        workspace_id=workspace_id,
        system=system,
        version=version,
    )


@app.command("unblock")
def unblock_job(
    job_id: Annotated[UUID, typer.Option("--job-id")],
    workspace_id: Annotated[UUID | None, typer.Option("--workspace-id")] = None,
    system: Annotated[bool, typer.Option("--system")] = False,
    version: Annotated[int | None, typer.Option("--version", min=1)] = None,
) -> None:
    _mutate_job(
        operation="unblock",
        job_id=job_id,
        workspace_id=workspace_id,
        system=system,
        version=version,
    )


@app.command("worker")
def worker(
    queues: Annotated[str, typer.Option("--queues")] = "ingestion,default,system",
    workspace_id: Annotated[UUID | None, typer.Option("--workspace-id")] = None,
    worker_id: Annotated[UUID | None, typer.Option("--worker-id")] = None,
    once: Annotated[bool, typer.Option("--once")] = False,
    poll_interval_seconds: Annotated[
        float, typer.Option("--poll-interval-seconds", min=0.1)
    ] = 5.0,
    drain_timeout_seconds: Annotated[
        float, typer.Option("--drain-timeout-seconds", min=0.0)
    ] = 30.0,
    concurrency: Annotated[int, typer.Option("--concurrency", min=1)] = 1,
    reaper_interval_seconds: Annotated[
        float, typer.Option("--reaper-interval-seconds", min=0.1)
    ] = 15.0,
    max_jobs: Annotated[int | None, typer.Option("--max-jobs", min=1)] = None,
) -> None:
    """Run the general worker over one or more comma-separated queues."""

    queue_names = _parse_queue_names(queues)
    factory, registry = _job_runtime()
    active_worker = JobWorker(
        session_factory=factory,
        registry=registry,
        queue_names=queue_names,
        worker_id=worker_id,
        workspace_id=workspace_id,
        max_concurrency=concurrency,
        reaper_interval_seconds=reaper_interval_seconds,
    )
    if once or max_jobs is not None:
        processed = 0
        while True:
            report = active_worker.run_once_sync()
            _echo_json(asdict(report))
            if report.status != "idle":
                processed += 1
            if once or report.status == "idle" or processed >= (max_jobs or 1):
                return
    asyncio.run(
        active_worker.run(
            poll_interval_seconds=poll_interval_seconds,
            drain_timeout_seconds=drain_timeout_seconds,
        )
    )


@app.command("scheduler")
def scheduler(
    poll_interval_seconds: Annotated[
        float, typer.Option("--poll-interval-seconds", min=0.1)
    ] = 30.0,
    once: Annotated[bool, typer.Option("--once")] = False,
    batch_size: Annotated[int, typer.Option("--batch-size", min=1, max=100)] = 100,
) -> None:
    """Expand durable schedules into ordinary jobs."""

    factory, registry = _job_runtime()
    while True:
        try:
            with factory() as session:
                created = JobScheduler(session=session, registry=registry).run_once(
                    now=datetime.now().astimezone(), batch_size=batch_size
                )
                session.commit()
        except Exception as exc:  # noqa: BLE001 - stable CLI boundary
            _exit_job_error(exc)
        _echo_json({"status": "ok", "created_jobs": created})
        if once:
            return
        time.sleep(poll_interval_seconds)


@schedules_app.command("create")
def create_schedule(
    name: Annotated[str, typer.Option("--name")],
    job_type: Annotated[str, typer.Option("--job-type")],
    cron_expression: Annotated[str, typer.Option("--cron")],
    workspace_id: Annotated[UUID | None, typer.Option("--workspace-id")] = None,
    system: Annotated[bool, typer.Option("--system")] = False,
    timezone: Annotated[str, typer.Option("--timezone")] = "UTC",
    payload_json: Annotated[str, typer.Option("--payload-json")] = "{}",
    description: Annotated[str | None, typer.Option("--description")] = None,
    handler_version: Annotated[int, typer.Option("--handler-version", min=1)] = 1,
    queue_name: Annotated[str | None, typer.Option("--queue")] = None,
    priority: Annotated[
        int | None, typer.Option("--priority", min=-1000, max=1000)
    ] = None,
    concurrency_key: Annotated[str | None, typer.Option("--concurrency-key")] = None,
    misfire_policy: Annotated[str, typer.Option("--misfire-policy")] = "run_once",
    max_catch_up: Annotated[int, typer.Option("--max-catch-up", min=1, max=100)] = 1,
) -> None:
    payload = _parse_payload_json(payload_json)
    scope, active_workspace_id = _resolve_scope(
        workspace_id=workspace_id, system=system
    )
    factory, registry = _job_runtime()
    try:
        with factory() as session:
            schedule = JobScheduleService(session=session, registry=registry).create(
                CreateJobScheduleRequest(
                    scope=scope,
                    workspace_id=active_workspace_id,
                    name=name,
                    description=description,
                    job_type=job_type,
                    handler_version=handler_version,
                    payload=payload,
                    queue_name=queue_name,
                    priority=priority,
                    concurrency_key=concurrency_key,
                    cron_expression=cron_expression,
                    timezone=timezone,
                    misfire_policy=misfire_policy,
                    max_catch_up=max_catch_up,
                ),
                actor=_CLI_ACTOR,
            )
            session.commit()
            response = JobScheduleResponse.model_validate(schedule)
    except Exception as exc:  # noqa: BLE001 - stable CLI boundary
        _exit_job_error(exc)
    _echo_json(response)


@schedules_app.command("list")
def list_schedules(
    workspace_id: Annotated[UUID | None, typer.Option("--workspace-id")] = None,
    system: Annotated[bool, typer.Option("--system")] = False,
) -> None:
    scope, active_workspace_id = _resolve_scope(
        workspace_id=workspace_id, system=system
    )
    factory, registry = _job_runtime()
    try:
        with factory() as session:
            rows = JobScheduleService(session=session, registry=registry).list(
                scope=scope, workspace_id=active_workspace_id
            )
            response = {
                "items": [
                    JobScheduleResponse.model_validate(row).model_dump(mode="json")
                    for row in rows
                ]
            }
    except Exception as exc:  # noqa: BLE001 - stable CLI boundary
        _exit_job_error(exc)
    _echo_json(response)


@schedules_app.command("show")
def show_schedule(
    schedule_id: Annotated[UUID, typer.Option("--schedule-id")],
    workspace_id: Annotated[UUID | None, typer.Option("--workspace-id")] = None,
    system: Annotated[bool, typer.Option("--system")] = False,
) -> None:
    scope, active_workspace_id = _resolve_scope(
        workspace_id=workspace_id, system=system
    )
    factory, registry = _job_runtime()
    try:
        with factory() as session:
            row = JobScheduleService(session=session, registry=registry).get(
                schedule_id=schedule_id,
                scope=scope,
                workspace_id=active_workspace_id,
            )
            response = JobScheduleResponse.model_validate(row)
    except Exception as exc:  # noqa: BLE001 - stable CLI boundary
        _exit_job_error(exc)
    _echo_json(response)


@schedules_app.command("pause")
def pause_schedule(
    schedule_id: Annotated[UUID, typer.Option("--schedule-id")],
    version: Annotated[int, typer.Option("--version", min=1)],
    workspace_id: Annotated[UUID | None, typer.Option("--workspace-id")] = None,
    system: Annotated[bool, typer.Option("--system")] = False,
) -> None:
    _schedule_action(
        operation="pause",
        schedule_id=schedule_id,
        version=version,
        workspace_id=workspace_id,
        system=system,
    )


@schedules_app.command("resume")
def resume_schedule(
    schedule_id: Annotated[UUID, typer.Option("--schedule-id")],
    version: Annotated[int, typer.Option("--version", min=1)],
    workspace_id: Annotated[UUID | None, typer.Option("--workspace-id")] = None,
    system: Annotated[bool, typer.Option("--system")] = False,
) -> None:
    _schedule_action(
        operation="resume",
        schedule_id=schedule_id,
        version=version,
        workspace_id=workspace_id,
        system=system,
    )


@schedules_app.command("run-now")
def run_schedule_now(
    schedule_id: Annotated[UUID, typer.Option("--schedule-id")],
    version: Annotated[int, typer.Option("--version", min=1)],
    workspace_id: Annotated[UUID | None, typer.Option("--workspace-id")] = None,
    system: Annotated[bool, typer.Option("--system")] = False,
) -> None:
    _schedule_action(
        operation="run-now",
        schedule_id=schedule_id,
        version=version,
        workspace_id=workspace_id,
        system=system,
    )


@schedules_app.command("archive")
def archive_schedule(
    schedule_id: Annotated[UUID, typer.Option("--schedule-id")],
    version: Annotated[int, typer.Option("--version", min=1)],
    workspace_id: Annotated[UUID | None, typer.Option("--workspace-id")] = None,
    system: Annotated[bool, typer.Option("--system")] = False,
) -> None:
    _schedule_action(
        operation="archive",
        schedule_id=schedule_id,
        version=version,
        workspace_id=workspace_id,
        system=system,
    )


@schedules_app.command("update")
def update_schedule(
    schedule_id: Annotated[UUID, typer.Option("--schedule-id")],
    version: Annotated[int, typer.Option("--version", min=1)],
    workspace_id: Annotated[UUID | None, typer.Option("--workspace-id")] = None,
    system: Annotated[bool, typer.Option("--system")] = False,
    name: Annotated[str | None, typer.Option("--name")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    payload_json: Annotated[str | None, typer.Option("--payload-json")] = None,
    queue_name: Annotated[str | None, typer.Option("--queue")] = None,
    priority: Annotated[
        int | None, typer.Option("--priority", min=-1000, max=1000)
    ] = None,
    concurrency_key: Annotated[str | None, typer.Option("--concurrency-key")] = None,
    cron_expression: Annotated[str | None, typer.Option("--cron")] = None,
    timezone: Annotated[str | None, typer.Option("--timezone")] = None,
    misfire_policy: Annotated[str | None, typer.Option("--misfire-policy")] = None,
    max_catch_up: Annotated[
        int | None, typer.Option("--max-catch-up", min=1, max=100)
    ] = None,
) -> None:
    payload = None if payload_json is None else _parse_payload_json(payload_json)
    scope, active_workspace_id = _resolve_scope(
        workspace_id=workspace_id, system=system
    )
    factory, registry = _job_runtime()
    try:
        with factory() as session:
            row = JobScheduleService(session=session, registry=registry).update(
                schedule_id=schedule_id,
                scope=scope,
                workspace_id=active_workspace_id,
                actor=_CLI_ACTOR,
                expected_version=version,
                name=name,
                description=description,
                payload=payload,
                queue_name=queue_name,
                priority=priority,
                concurrency_key=concurrency_key,
                cron_expression=cron_expression,
                timezone=timezone,
                misfire_policy=misfire_policy,
                max_catch_up=max_catch_up,
            )
            session.commit()
            response = JobScheduleResponse.model_validate(row)
    except Exception as exc:  # noqa: BLE001 - stable CLI boundary
        _exit_job_error(exc)
    _echo_json(response)


@queues_app.command("list")
def list_queues() -> None:
    factory, registry = _job_runtime()
    try:
        with factory() as session:
            rows = JobService(session=session, registry=registry).list_queues()
            response = [
                JobQueueResponse.model_validate(row).model_dump(mode="json")
                for row in rows
            ]
    except Exception as exc:  # noqa: BLE001 - stable CLI boundary
        _exit_job_error(exc)
    _echo_json({"items": response})


@queues_app.command("pause")
def pause_queue(
    queue_name: Annotated[str, typer.Option("--queue")],
    version: Annotated[int, typer.Option("--version", min=1)],
) -> None:
    _configure_queue(queue_name=queue_name, version=version, paused=True)


@queues_app.command("resume")
def resume_queue(
    queue_name: Annotated[str, typer.Option("--queue")],
    version: Annotated[int, typer.Option("--version", min=1)],
) -> None:
    _configure_queue(queue_name=queue_name, version=version, paused=False)


@queues_app.command("configure")
def configure_queue(
    queue_name: Annotated[str, typer.Option("--queue")],
    version: Annotated[int, typer.Option("--version", min=1)],
    global_concurrency_limit: Annotated[
        int | None, typer.Option("--global-concurrency-limit", min=1)
    ] = None,
    workspace_concurrency_limit: Annotated[
        int | None, typer.Option("--workspace-concurrency-limit", min=1)
    ] = None,
    default_lease_seconds: Annotated[
        int | None, typer.Option("--default-lease-seconds", min=15, max=3600)
    ] = None,
) -> None:
    _configure_queue(
        queue_name=queue_name,
        version=version,
        global_concurrency_limit=global_concurrency_limit,
        workspace_concurrency_limit=workspace_concurrency_limit,
        default_lease_seconds=default_lease_seconds,
    )


@workers_app.command("list")
def list_workers(
    limit: Annotated[int, typer.Option("--limit", min=1, max=500)] = 200,
) -> None:
    factory, registry = _job_runtime()
    try:
        with factory() as session:
            rows = JobService(session=session, registry=registry).list_workers(
                limit=limit
            )
            response = [
                JobWorkerResponse.model_validate(row).model_dump(mode="json")
                for row in rows
            ]
    except Exception as exc:  # noqa: BLE001 - stable CLI boundary
        _exit_job_error(exc)
    _echo_json({"items": response})


@app.command("enqueue-ingest-source")
def enqueue_ingest_source(
    workspace_id: Annotated[UUID, typer.Option("--workspace-id")],
    source_id: Annotated[UUID, typer.Option("--source-id")],
    priority: Annotated[int, typer.Option("--priority")] = 0,
    max_attempts: Annotated[int, typer.Option("--max-attempts", min=1)] = 3,
) -> None:
    with session_scope() as session:
        try:
            job = ingestion_ops.enqueue_source_ingestion(
                session,
                workspace_id=workspace_id,
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
    workspace_id: Annotated[UUID | None, typer.Option("--workspace-id")] = None,
    system: Annotated[bool, typer.Option("--system")] = False,
    status: Annotated[str | None, typer.Option("--status")] = None,
    job_type: Annotated[str | None, typer.Option("--job-type")] = None,
    queue_name: Annotated[str | None, typer.Option("--queue")] = None,
    cursor: Annotated[str | None, typer.Option("--cursor")] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=200)] = 50,
) -> None:
    scope, active_workspace_id = _resolve_scope(
        workspace_id=workspace_id, system=system
    )
    factory, registry = _job_runtime()
    try:
        with factory() as session:
            page = JobService(session=session, registry=registry).list_jobs(
                scope=scope,
                workspace_id=active_workspace_id,
                limit=limit,
                cursor=cursor,
                status=status,
                queue_name=queue_name,
                job_type=job_type,
            )
            response = JobPageResponse.from_page(page)
    except Exception as exc:  # noqa: BLE001 - stable CLI boundary
        _exit_job_error(exc)
    _echo_json(response)


@app.command("show")
def show_job(
    job_id: Annotated[UUID, typer.Option("--job-id")],
    workspace_id: Annotated[UUID | None, typer.Option("--workspace-id")] = None,
    system: Annotated[bool, typer.Option("--system")] = False,
    history_limit: Annotated[
        int, typer.Option("--history-limit", min=1, max=200)
    ] = 100,
) -> None:
    scope, active_workspace_id = _resolve_scope(
        workspace_id=workspace_id, system=system
    )
    factory, registry = _job_runtime()
    try:
        with factory() as session:
            detail = JobService(session=session, registry=registry).get_detail(
                scope=scope,
                workspace_id=active_workspace_id,
                job_id=job_id,
                history_limit=history_limit,
            )
            response = JobDetailResponse.from_detail(detail)
    except Exception as exc:  # noqa: BLE001 - stable CLI boundary
        _exit_job_error(exc)
    _echo_json(response)


@app.command("retry")
def retry_job(
    job_id: Annotated[UUID, typer.Option("--job-id")],
    workspace_id: Annotated[UUID | None, typer.Option("--workspace-id")] = None,
    system: Annotated[bool, typer.Option("--system")] = False,
    version: Annotated[int | None, typer.Option("--version", min=1)] = None,
    reset_retry_count: Annotated[
        bool, typer.Option("--reset-retry-count")
    ] = False,
) -> None:
    _mutate_job(
        operation="retry",
        job_id=job_id,
        workspace_id=workspace_id,
        system=system,
        version=version,
        reset_retry_count=reset_retry_count,
    )


@app.command("run-worker")
def run_worker(
    workspace_id: Annotated[UUID, typer.Option("--workspace-id")],
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
            workspace_id=workspace_id,
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
    workspace_id: UUID,
    worker_id: str,
    lease_seconds: int,
    processed_jobs: int,
) -> dict[str, object]:
    with session_scope() as session:
        report = ingestion_ops.run_next_ingestion_job(
            session,
            workspace_id=workspace_id,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
        )
        session.commit()

    payload: dict[str, object] = {
        "status": report.status,
        "workspace_id": str(report.workspace_id),
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


def _job_runtime() -> tuple[sessionmaker[Session], JobRegistry]:
    factory = create_job_session_factory()
    return factory, build_ingestion_registry(session_factory=factory)


def _resolve_scope(
    *, workspace_id: UUID | None, system: bool
) -> tuple[JobScope, UUID | None]:
    if system == (workspace_id is not None):
        typer.echo("provide exactly one of --workspace-id or --system", err=True)
        raise typer.Exit(2)
    if system:
        return "system", None
    return "workspace", workspace_id


def _parse_payload_json(raw: str) -> dict[str, object]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        typer.echo(f"invalid --payload-json: {exc.msg}", err=True)
        raise typer.Exit(2) from exc
    if not isinstance(parsed, dict):
        typer.echo("--payload-json must be a JSON object", err=True)
        raise typer.Exit(2)
    return parsed


def _parse_queue_names(raw: str) -> tuple[str, ...]:
    names = tuple(
        dict.fromkeys(part.strip() for part in raw.split(",") if part.strip())
    )
    if not names:
        typer.echo("--queues must contain at least one queue", err=True)
        raise typer.Exit(2)
    return names


def _mutate_job(
    *,
    operation: str,
    job_id: UUID,
    workspace_id: UUID | None,
    system: bool,
    version: int | None,
    reset_retry_count: bool = False,
) -> None:
    scope, active_workspace_id = _resolve_scope(
        workspace_id=workspace_id, system=system
    )
    factory, registry = _job_runtime()
    try:
        with factory() as session:
            service = JobService(session=session, registry=registry)
            if operation == "cancel":
                snapshot = service.cancel(
                    scope=scope,
                    workspace_id=active_workspace_id,
                    job_id=job_id,
                    actor=_CLI_ACTOR,
                    expected_version=version,
                )
            elif operation == "retry":
                snapshot = service.retry(
                    scope=scope,
                    workspace_id=active_workspace_id,
                    job_id=job_id,
                    actor=_CLI_ACTOR,
                    expected_version=version,
                    reset_retry_count=reset_retry_count,
                )
            else:
                snapshot = service.unblock(
                    scope=scope,
                    workspace_id=active_workspace_id,
                    job_id=job_id,
                    actor=_CLI_ACTOR,
                    expected_version=version,
                )
            session.commit()
            response = BackgroundJobResponse.from_snapshot(snapshot)
    except Exception as exc:  # noqa: BLE001 - stable CLI boundary
        _exit_job_error(exc)
    _echo_json(response)


def _schedule_action(
    *,
    operation: str,
    schedule_id: UUID,
    version: int,
    workspace_id: UUID | None,
    system: bool,
) -> None:
    scope, active_workspace_id = _resolve_scope(
        workspace_id=workspace_id, system=system
    )
    factory, registry = _job_runtime()
    try:
        with factory() as session:
            service = JobScheduleService(session=session, registry=registry)
            if operation == "pause":
                row = service.pause(
                    schedule_id=schedule_id,
                    scope=scope,
                    workspace_id=active_workspace_id,
                    actor=_CLI_ACTOR,
                    expected_version=version,
                )
                response: object = JobScheduleResponse.model_validate(row)
            elif operation == "resume":
                row = service.resume(
                    schedule_id=schedule_id,
                    scope=scope,
                    workspace_id=active_workspace_id,
                    actor=_CLI_ACTOR,
                    expected_version=version,
                )
                response = JobScheduleResponse.model_validate(row)
            elif operation == "archive":
                row = service.archive(
                    schedule_id=schedule_id,
                    scope=scope,
                    workspace_id=active_workspace_id,
                    actor=_CLI_ACTOR,
                    expected_version=version,
                )
                response = JobScheduleResponse.model_validate(row)
            else:
                job = service.run_now(
                    schedule_id=schedule_id,
                    scope=scope,
                    workspace_id=active_workspace_id,
                    actor=_CLI_ACTOR,
                    expected_version=version,
                )
                response = BackgroundJobResponse.from_snapshot(
                    JobService(session=session, registry=registry).snapshot(job)
                )
            session.commit()
    except Exception as exc:  # noqa: BLE001 - stable CLI boundary
        _exit_job_error(exc)
    _echo_json(response)


def _configure_queue(
    *,
    queue_name: str,
    version: int,
    paused: bool | None = None,
    global_concurrency_limit: int | None = None,
    workspace_concurrency_limit: int | None = None,
    default_lease_seconds: int | None = None,
) -> None:
    factory, registry = _job_runtime()
    try:
        with factory() as session:
            row = JobService(session=session, registry=registry).configure_queue(
                queue_name=queue_name,
                actor=_CLI_ACTOR,
                expected_version=version,
                paused=paused,
                global_concurrency_limit=global_concurrency_limit,
                workspace_concurrency_limit=workspace_concurrency_limit,
                default_lease_seconds=default_lease_seconds,
            )
            session.commit()
            response = JobQueueResponse.model_validate(row)
    except Exception as exc:  # noqa: BLE001 - stable CLI boundary
        _exit_job_error(exc)
    _echo_json(response)


def _echo_json(value: object) -> None:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    typer.echo(json.dumps(value, default=_json_default))


def _json_default(value: object) -> object:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _default_worker_id() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


def _exit_ingestion_ops_error(error: ingestion_ops.IngestionOpsError) -> NoReturn:
    typer.echo(error.detail, err=True)
    raise typer.Exit(1)


def _exit_job_error(error: Exception) -> NoReturn:
    typer.echo(str(error) or error.__class__.__name__, err=True)
    raise typer.Exit(1)
