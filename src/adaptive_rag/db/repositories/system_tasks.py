"""Repository for global system task lease and last-run state."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.system_task import SystemTaskState


class SystemTaskRepository:
    """Persistence for system-wide scheduled tasks.

    Transactions are controlled by the caller. Methods flush but do not commit.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, task_id: str) -> SystemTaskState | None:
        return self._session.get(SystemTaskState, task_id)

    def list_tasks(self) -> list[SystemTaskState]:
        statement = select(SystemTaskState).order_by(SystemTaskState.task_id)
        return list(self._session.scalars(statement))

    def ensure(
        self,
        *,
        task_id: str,
        interval_seconds: int,
    ) -> SystemTaskState:
        task_id = _normalize_task_id(task_id)
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        row = self.get(task_id)
        if row is None:
            row = SystemTaskState(
                task_id=task_id,
                interval_seconds=interval_seconds,
            )
            self._session.add(row)
        else:
            row.interval_seconds = interval_seconds
        self._session.flush()
        return row

    def try_lease(
        self,
        *,
        task_id: str,
        worker_id: str,
        lease_seconds: int,
        interval_seconds: int,
        force: bool = False,
        now: datetime | None = None,
    ) -> SystemTaskState | None:
        """Acquire an exclusive lease when the task is due (or force=True).

        Returns the leased row, or None when another worker holds the lease or
        the task is not due yet.
        """

        task_id = _normalize_task_id(task_id)
        worker_id = worker_id.strip()
        if not worker_id:
            raise ValueError("worker_id must not be empty")
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")

        active_now = now or utc_now()
        self.ensure(task_id=task_id, interval_seconds=interval_seconds)

        # Serialize concurrent leasers (Postgres SKIP LOCKED not needed for one row).
        locked = self._session.scalars(
            select(SystemTaskState)
            .where(SystemTaskState.task_id == task_id)
            .with_for_update()
        ).one()

        active_now = _as_utc(active_now)
        if (
            locked.locked_until is not None
            and _as_utc(locked.locked_until) > active_now
            and locked.locked_by != worker_id
        ):
            return None

        if not force and not _is_due(locked, now=active_now):
            return None

        locked.locked_by = worker_id
        locked.locked_until = active_now + timedelta(seconds=lease_seconds)
        locked.last_started_at = active_now
        locked.last_status = "running"
        locked.last_error = None
        self._session.flush()
        return locked

    def mark_succeeded(
        self,
        *,
        task_id: str,
        worker_id: str,
        report: Mapping[str, Any] | None = None,
        now: datetime | None = None,
    ) -> SystemTaskState | None:
        row = self.get(task_id)
        if row is None:
            return None
        if row.locked_by is not None and row.locked_by != worker_id:
            return None
        active_now = now or utc_now()
        row.last_succeeded_at = active_now
        row.last_status = "succeeded"
        row.last_error = None
        row.last_report_json = dict(report) if report is not None else None
        row.locked_by = None
        row.locked_until = None
        self._session.flush()
        return row

    def mark_failed(
        self,
        *,
        task_id: str,
        worker_id: str,
        error: str,
        report: Mapping[str, Any] | None = None,
        now: datetime | None = None,
    ) -> SystemTaskState | None:
        row = self.get(task_id)
        if row is None:
            return None
        if row.locked_by is not None and row.locked_by != worker_id:
            return None
        # Touch updated_at even when clocks are frozen in tests.
        _ = now or utc_now()
        row.last_status = "failed"
        row.last_error = error[:2000]
        row.last_report_json = dict(report) if report is not None else None
        row.locked_by = None
        row.locked_until = None
        self._session.flush()
        return row


def _is_due(row: SystemTaskState, *, now: datetime) -> bool:
    if row.last_succeeded_at is None:
        return True
    elapsed = (
        _as_utc(now) - _as_utc(row.last_succeeded_at)
    ).total_seconds()
    return elapsed >= float(row.interval_seconds)


def _as_utc(value: datetime) -> datetime:
    """Normalize SQLite-naive datetimes to aware UTC for comparisons."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_task_id(task_id: str) -> str:
    normalized = task_id.strip()
    if not normalized:
        raise ValueError("task_id must not be empty")
    return normalized
