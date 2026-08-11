"""Bounded aggregate snapshot for the job-platform control plane."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Job, JobQueue, JobSchedule, JobWorker


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
            queue_name: created_at
            for queue_name, created_at in self._session.execute(
                select(Job.queue_name, func.min(Job.created_at))
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
                .where(Job.status == "queued")
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
            },
            "unroutable_queued": unroutable,
            "scheduler_lag_seconds": (
                0.0
                if scheduler_due is None
                else max(
                    0.0,
                    (_as_utc(now) - _as_utc(scheduler_due)).total_seconds(),
                )
            ),
        }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = ["JobMetricsService"]
