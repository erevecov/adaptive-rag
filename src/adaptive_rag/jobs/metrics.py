"""Bounded aggregate snapshot for the job-platform control plane."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import (
    Job,
    JobAttempt,
    JobEvent,
    JobQueue,
    JobSchedule,
    JobWorker,
)

_METRIC_SAMPLE_LIMIT = 10_000


class JobMetricsService:
    def __init__(self, *, session: Session) -> None:
        self._session = session

    def snapshot(self, *, now: datetime) -> dict[str, Any]:
        stale_before = now - timedelta(seconds=30)
        queues = list(
            self._session.scalars(select(JobQueue).order_by(JobQueue.name).limit(100))
        )
        grouped = list(
            self._session.execute(
                select(Job.queue_name, Job.status, func.count(Job.id))
                .group_by(Job.queue_name, Job.status)
                .limit(1000)
            )
        )
        counts = {
            (queue_name, status): int(count) for queue_name, status, count in grouped
        }
        oldest = {
            queue_name: eligible_at
            for queue_name, eligible_at in self._session.execute(
                select(Job.queue_name, func.min(Job.run_after))
                .where(Job.status == "queued", Job.run_after <= now)
                .group_by(Job.queue_name)
                .limit(100)
            )
        }
        workers = list(
            self._session.scalars(
                select(JobWorker).order_by(JobWorker.heartbeat_at.desc()).limit(500)
            )
        )
        routable = {
            (queue_name, handler)
            for worker in workers
            if worker.shutdown_at is None
            and _as_utc(worker.heartbeat_at) >= _as_utc(stale_before)
            for queue_name in worker.supported_queues
            for handler in worker.supported_handlers
        }
        unroutable = sum(
            int(count)
            for queue_name, job_type, handler_version, count in self._session.execute(
                select(
                    Job.queue_name,
                    Job.job_type,
                    Job.handler_version,
                    func.count(Job.id),
                )
                .where(Job.status == "queued", Job.run_after <= now)
                .group_by(Job.queue_name, Job.job_type, Job.handler_version)
                .limit(1000)
            )
            if (queue_name, f"{job_type}@{handler_version}") not in routable
        )
        scheduler_due = self._session.scalar(
            select(func.min(JobSchedule.next_run_at)).where(
                JobSchedule.paused_at.is_(None),
                JobSchedule.archived_at.is_(None),
                JobSchedule.next_run_at <= now,
            )
        )
        scheduled_timings = list(
            self._session.execute(
                select(Job.scheduled_for, Job.created_at)
                .where(
                    Job.schedule_id.is_not(None),
                    Job.scheduled_for.is_not(None),
                )
                .order_by(Job.created_at.desc())
                .limit(_METRIC_SAMPLE_LIMIT)
            )
        )
        scheduler_misfires = sum(
            (_as_utc(created_at) - _as_utc(scheduled_for)).total_seconds() > 60
            for scheduled_for, created_at in scheduled_timings
        )
        attempt_timings = list(
            self._session.execute(
                select(Job.created_at, JobAttempt.started_at, JobAttempt.finished_at)
                .join(JobAttempt, JobAttempt.job_id == Job.id)
                .where(JobAttempt.started_at.is_not(None))
                .order_by(JobAttempt.started_at.desc())
                .limit(_METRIC_SAMPLE_LIMIT)
            )
        )
        enqueue_to_start = [
            max(0.0, (_as_utc(started) - _as_utc(created)).total_seconds())
            for created, started, _finished in attempt_timings
        ]
        execution_duration = [
            max(0.0, (_as_utc(finished) - _as_utc(started)).total_seconds())
            for _created, started, finished in attempt_timings
            if finished is not None
        ]
        retry_count = int(self._session.scalar(select(func.sum(Job.retry_count))) or 0)
        event_counts = {
            event_type: int(count)
            for event_type, count in self._session.execute(
                select(JobEvent.event_type, func.count(JobEvent.id))
                .where(
                    JobEvent.event_type.in_(
                        (
                            "blocked",
                            "dead_lettered",
                            "cancelled",
                            "expired",
                            "fenced_write_rejected",
                        )
                    )
                )
                .group_by(JobEvent.event_type)
                .limit(10)
            )
        }
        running_by_handler = {
            f"{job_type}@{version}": int(count)
            for job_type, version, count in self._session.execute(
                select(Job.job_type, Job.handler_version, func.count(Job.id))
                .where(Job.status == "running")
                .group_by(Job.job_type, Job.handler_version)
                .limit(1000)
            )
        }
        running_by_workspace = {
            "system" if workspace_id is None else str(workspace_id): int(count)
            for workspace_id, count in self._session.execute(
                select(Job.workspace_id, func.count(Job.id))
                .where(Job.status == "running")
                .group_by(Job.workspace_id)
                .limit(1000)
            )
        }
        return {
            "generated_at": now.isoformat(),
            "queues": [
                {
                    "name": queue.name,
                    "queued": counts.get((queue.name, "queued"), 0),
                    "running": counts.get((queue.name, "running"), 0),
                    "blocked": counts.get((queue.name, "blocked"), 0),
                    "dead_letter": counts.get((queue.name, "dead_letter"), 0),
                    "oldest_eligible_age_seconds": (
                        None
                        if oldest.get(queue.name) is None
                        else max(
                            0.0,
                            (
                                _as_utc(now) - _as_utc(oldest[queue.name])
                            ).total_seconds(),
                        )
                    ),
                    "global_concurrency_limit": queue.global_concurrency_limit,
                    "available_capacity": (
                        None
                        if queue.global_concurrency_limit is None
                        else max(
                            0,
                            queue.global_concurrency_limit
                            - counts.get((queue.name, "running"), 0),
                        )
                    ),
                }
                for queue in queues
            ],
            "workers": {
                "live": sum(
                    worker.shutdown_at is None
                    and worker.draining_at is None
                    and _as_utc(worker.heartbeat_at) >= _as_utc(stale_before)
                    for worker in workers
                ),
                "stale": sum(
                    worker.shutdown_at is None
                    and _as_utc(worker.heartbeat_at) < _as_utc(stale_before)
                    for worker in workers
                ),
                "draining": sum(
                    worker.shutdown_at is None and worker.draining_at is not None
                    for worker in workers
                ),
                "advertised_capacity": sum(
                    worker.max_concurrency
                    for worker in workers
                    if worker.shutdown_at is None
                    and worker.draining_at is None
                    and _as_utc(worker.heartbeat_at) >= _as_utc(stale_before)
                ),
            },
            "unroutable_queued": unroutable,
            "running": {
                "total": sum(
                    count
                    for (queue_name, status), count in counts.items()
                    if queue_name and status == "running"
                ),
                "by_handler": running_by_handler,
                "by_workspace": running_by_workspace,
            },
            "timings": {
                "enqueue_to_start_seconds": _summary(enqueue_to_start),
                "execution_duration_seconds": _summary(execution_duration),
                "sample_limit": _METRIC_SAMPLE_LIMIT,
            },
            "outcomes": {
                "retries": retry_count,
                "blocks": event_counts.get("blocked", 0),
                "dead_letters": event_counts.get("dead_lettered", 0),
                "cancellations": event_counts.get("cancelled", 0),
                "expired_leases": event_counts.get("expired", 0),
                "fenced_write_rejections": event_counts.get(
                    "fenced_write_rejected", 0
                ),
            },
            "scheduler_lag_seconds": (
                0.0
                if scheduler_due is None
                else max(
                    0.0,
                    (_as_utc(now) - _as_utc(scheduler_due)).total_seconds(),
                )
            ),
            "scheduler_misfires": scheduler_misfires,
        }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "max": None, "p50": None, "p95": None}
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "max": ordered[-1],
        "p50": _nearest_rank(ordered, 0.50),
        "p95": _nearest_rank(ordered, 0.95),
    }


def _nearest_rank(ordered: list[float], quantile: float) -> float:
    index = max(0, min(len(ordered) - 1, int(len(ordered) * quantile + 0.999999) - 1))
    return ordered[index]


__all__ = ["JobMetricsService"]
