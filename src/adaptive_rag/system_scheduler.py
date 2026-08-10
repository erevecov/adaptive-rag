"""In-app system scheduler for global maintenance tasks.

Runs inside the product stack (Compose ``scheduler`` service / CLI loop), not as
host crontab. Tasks use ``system_task_state`` for daily intervals and leasing so
multiple replicas cannot double-run the same task.

Current tasks (Alibaba/Qwen only for pricing):
- ``provider_model_pricing_sync`` — update catalog ``pricing_json`` from
  published Model Studio international list prices.
"""

from __future__ import annotations

import logging
import os
import socket
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.system_task import (
    PROVIDER_MODEL_PRICING_SYNC_TASK_ID,
    SystemTaskState,
)
from adaptive_rag.db.repositories.system_tasks import SystemTaskRepository
from adaptive_rag.provider_pricing import (
    PricingSyncReport,
    sync_provider_model_pricing,
)

logger = logging.getLogger(__name__)

DEFAULT_PRICING_INTERVAL_SECONDS = 86_400  # 24h
DEFAULT_LEASE_SECONDS = 300
DEFAULT_POLL_INTERVAL_SECONDS = 60.0

TaskHandler = Callable[[Session], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class SystemTaskDefinition:
    task_id: str
    interval_seconds: int
    handler: TaskHandler


@dataclass(frozen=True, slots=True)
class SystemTaskRunResult:
    task_id: str
    status: str  # ran | skipped_not_due | skipped_locked | failed
    worker_id: str
    force: bool
    report: dict[str, Any] | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_system_tasks(
    *,
    pricing_interval_seconds: int = DEFAULT_PRICING_INTERVAL_SECONDS,
) -> tuple[SystemTaskDefinition, ...]:
    return (
        SystemTaskDefinition(
            task_id=PROVIDER_MODEL_PRICING_SYNC_TASK_ID,
            interval_seconds=pricing_interval_seconds,
            handler=_handle_provider_model_pricing_sync,
        ),
    )


def _handle_provider_model_pricing_sync(session: Session) -> dict[str, Any]:
    report: PricingSyncReport = sync_provider_model_pricing(session, dry_run=False)
    return report.as_dict()


def run_system_task(
    session: Session,
    *,
    task: SystemTaskDefinition,
    worker_id: str,
    force: bool = False,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: datetime | None = None,
) -> SystemTaskRunResult:
    """Lease and execute one system task when due (or force)."""

    repo = SystemTaskRepository(session)
    active_now = now or utc_now()
    leased = repo.try_lease(
        task_id=task.task_id,
        worker_id=worker_id,
        lease_seconds=lease_seconds,
        interval_seconds=task.interval_seconds,
        force=force,
        now=active_now,
    )
    if leased is None:
        existing = repo.get(task.task_id)
        locked_until = existing.locked_until if existing is not None else None
        if (
            existing is not None
            and locked_until is not None
            and _as_utc(locked_until) > _as_utc(active_now)
            and existing.locked_by != worker_id
        ):
            status = "skipped_locked"
        else:
            status = "skipped_not_due"
        return SystemTaskRunResult(
            task_id=task.task_id,
            status=status,
            worker_id=worker_id,
            force=force,
        )

    try:
        report = dict(task.handler(session))
    except Exception as exc:
        message = str(exc)
        repo.mark_failed(
            task_id=task.task_id,
            worker_id=worker_id,
            error=message,
            now=utc_now(),
        )
        logger.exception(
            "system_task_failed",
            extra={"task_id": task.task_id, "worker_id": worker_id},
        )
        return SystemTaskRunResult(
            task_id=task.task_id,
            status="failed",
            worker_id=worker_id,
            force=force,
            error=message,
        )

    repo.mark_succeeded(
        task_id=task.task_id,
        worker_id=worker_id,
        report=report,
        now=utc_now(),
    )
    logger.info(
        "system_task_succeeded",
        extra={
            "task_id": task.task_id,
            "worker_id": worker_id,
            "force": force,
        },
    )
    return SystemTaskRunResult(
        task_id=task.task_id,
        status="ran",
        worker_id=worker_id,
        force=force,
        report=report,
    )


def run_due_system_tasks(
    session: Session,
    *,
    worker_id: str,
    force: bool = False,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    tasks: tuple[SystemTaskDefinition, ...] | None = None,
    now: datetime | None = None,
) -> list[SystemTaskRunResult]:
    """Run all registered system tasks that are due (or all when force=True)."""

    active_tasks = tasks if tasks is not None else default_system_tasks()
    return [
        run_system_task(
            session,
            task=task,
            worker_id=worker_id,
            force=force,
            lease_seconds=lease_seconds,
            now=now,
        )
        for task in active_tasks
    ]


def run_provider_pricing_system_task(
    session: Session,
    *,
    worker_id: str,
    force: bool = True,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    dry_run: bool = False,
) -> SystemTaskRunResult:
    """Manual/smoke entry for pricing sync via system-task lease path.

    When ``dry_run`` is True, runs the pure pricing sync without leasing or
    mutating ``system_task_state``.
    """

    if dry_run:
        report = sync_provider_model_pricing(session, dry_run=True)
        return SystemTaskRunResult(
            task_id=PROVIDER_MODEL_PRICING_SYNC_TASK_ID,
            status="ran",
            worker_id=worker_id,
            force=force,
            report=report.as_dict(),
        )

    task = SystemTaskDefinition(
        task_id=PROVIDER_MODEL_PRICING_SYNC_TASK_ID,
        interval_seconds=DEFAULT_PRICING_INTERVAL_SECONDS,
        handler=_handle_provider_model_pricing_sync,
    )
    return run_system_task(
        session,
        task=task,
        worker_id=worker_id,
        force=force,
        lease_seconds=lease_seconds,
    )


def system_task_status_payload(row: SystemTaskState) -> dict[str, Any]:
    return {
        "task_id": row.task_id,
        "interval_seconds": row.interval_seconds,
        "last_started_at": (
            row.last_started_at.isoformat() if row.last_started_at else None
        ),
        "last_succeeded_at": (
            row.last_succeeded_at.isoformat() if row.last_succeeded_at else None
        ),
        "last_status": row.last_status,
        "last_error": row.last_error,
        "last_report": row.last_report_json,
        "locked_by": row.locked_by,
        "locked_until": (
            row.locked_until.isoformat() if row.locked_until else None
        ),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def ensure_registered_tasks(
    session: Session,
    *,
    tasks: tuple[SystemTaskDefinition, ...] | None = None,
) -> list[SystemTaskState]:
    """Upsert interval rows for all known system tasks."""

    repo = SystemTaskRepository(session)
    active = tasks if tasks is not None else default_system_tasks()
    return [
        repo.ensure(task_id=task.task_id, interval_seconds=task.interval_seconds)
        for task in active
    ]


def default_worker_id(prefix: str = "system-scheduler") -> str:
    return f"{prefix}-{socket.gethostname()}-{os.getpid()}"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def run_scheduler_loop(
    *,
    worker_id: str | None = None,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    once: bool = False,
    force: bool = False,
    session_factory: Callable[[], Any] | None = None,
) -> None:
    """Long-running loop used by the Compose/prod system scheduler process.

    ``session_factory`` is injectable for tests; default opens ``session_scope``.
    """

    from adaptive_rag.db.session import session_scope

    active_worker = worker_id or default_worker_id()
    logger.info(
        "system_scheduler_started",
        extra={
            "worker_id": active_worker,
            "poll_interval_seconds": poll_interval_seconds,
            "lease_seconds": lease_seconds,
        },
    )

    while True:
        if session_factory is not None:
            session = session_factory()
            try:
                results = run_due_system_tasks(
                    session,
                    worker_id=active_worker,
                    force=force,
                    lease_seconds=lease_seconds,
                )
                session.commit()
            finally:
                session.close()
        else:
            with session_scope() as session:
                results = run_due_system_tasks(
                    session,
                    worker_id=active_worker,
                    force=force,
                    lease_seconds=lease_seconds,
                )
                session.commit()

        for result in results:
            logger.info(
                "system_scheduler_tick",
                extra={"system_task": result.as_dict()},
            )

        if once:
            return
        # force only applies to the first tick (smoke), then resume due-only.
        force = False
        time.sleep(poll_interval_seconds)
