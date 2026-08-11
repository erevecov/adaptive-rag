"""Compatibility CLI aliases for the general durable job scheduler."""

from __future__ import annotations

import json
from typing import Annotated

import typer

from adaptive_rag.system_scheduler import (
    DEFAULT_LEASE_SECONDS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    default_worker_id,
    ensure_registered_tasks,
    run_provider_pricing_system_task,
    run_scheduler_loop,
    system_task_status_payload,
)

app = typer.Typer(no_args_is_help=True)


@app.command("run-scheduler")
def run_scheduler(
    worker_id: Annotated[str | None, typer.Option("--worker-id")] = None,
    poll_interval_seconds: Annotated[
        float,
        typer.Option("--poll-interval-seconds", min=0.1),
    ] = DEFAULT_POLL_INTERVAL_SECONDS,
    lease_seconds: Annotated[
        int,
        typer.Option("--lease-seconds", min=1),
    ] = DEFAULT_LEASE_SECONDS,
    once: Annotated[
        bool,
        typer.Option(
            "--once",
            help="Evaluate due tasks once and exit (Compose health / smoke).",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Run tasks even if the daily interval has not elapsed.",
        ),
    ] = False,
) -> None:
    """Compatibility alias for the durable scheduler/system-task adapter.

    New deployments use ``jobs scheduler``. PostgreSQL installations delegate
    through the same durable schedules; legacy SQLite flows retain interval-task
    behavior until their compatibility surface is removed separately.
    """

    run_scheduler_loop(
        worker_id=worker_id,
        poll_interval_seconds=poll_interval_seconds,
        lease_seconds=lease_seconds,
        once=once,
        force=force,
    )


@app.command("list-tasks")
def list_tasks() -> None:
    """Show registered system tasks and last-run state (no secrets)."""

    from adaptive_rag.db.session import session_scope

    with session_scope() as session:
        rows = ensure_registered_tasks(session)
        session.commit()
        payload = {"items": [system_task_status_payload(row) for row in rows]}
    typer.echo(json.dumps(payload))


@app.command("run-pricing-sync")
def run_pricing_sync(
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    worker_id: Annotated[str | None, typer.Option("--worker-id")] = None,
) -> None:
    """Force provider model pricing sync (smoke / admin).

    Same path as the daily system task; uses lease + updates last_succeeded_at
    unless ``--dry-run``.
    """

    from adaptive_rag.db.session import session_scope

    active_worker = worker_id or default_worker_id(prefix="cli-pricing")
    with session_scope() as session:
        result = run_provider_pricing_system_task(
            session,
            worker_id=active_worker,
            force=True,
            dry_run=dry_run,
        )
        if not dry_run:
            session.commit()
        typer.echo(json.dumps(result.as_dict()))
