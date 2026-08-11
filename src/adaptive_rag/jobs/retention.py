"""Bounded, audit-aware retention for terminal background jobs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, delete, exists, or_, select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Job, ProviderUsage


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    succeeded_after: timedelta = timedelta(days=30)
    cancelled_after: timedelta = timedelta(days=30)
    dead_letter_after: timedelta = timedelta(days=90)

    def __post_init__(self) -> None:
        for field_name in (
            "succeeded_after",
            "cancelled_after",
            "dead_letter_after",
        ):
            if getattr(self, field_name) <= timedelta(0):
                raise ValueError(f"{field_name} must be positive")


@dataclass(frozen=True, slots=True)
class RetentionReport:
    dry_run: bool
    candidate_jobs: int
    deleted_jobs: int
    job_ids: tuple[UUID, ...]
    by_status: dict[str, int]


class JobRetention:
    """Selects and deletes one bounded batch in the caller transaction."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def run(
        self,
        *,
        policy: RetentionPolicy,
        now: datetime,
        dry_run: bool = True,
        batch_size: int = 1_000,
    ) -> RetentionReport:
        if now.tzinfo is None:
            raise ValueError("retention now must be timezone-aware")
        if not 1 <= batch_size <= 10_000:
            raise ValueError("batch_size must be within [1, 10000]")

        eligible_by_status = or_(
            and_(
                Job.status == "succeeded",
                Job.finished_at < now - policy.succeeded_after,
            ),
            and_(
                Job.status == "cancelled",
                Job.finished_at < now - policy.cancelled_after,
            ),
            and_(
                Job.status == "dead_letter",
                Job.finished_at < now - policy.dead_letter_after,
            ),
        )
        has_provider_usage = exists(
            select(ProviderUsage.id).where(ProviderUsage.job_id == Job.id)
        )
        rows = list(
            self._session.execute(
                select(Job.id, Job.status)
                .where(eligible_by_status, ~has_provider_usage)
                .order_by(Job.finished_at, Job.id)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
        )
        job_ids = tuple(row.id for row in rows)
        by_status: dict[str, int] = {}
        for row in rows:
            by_status[row.status] = by_status.get(row.status, 0) + 1

        deleted_jobs = 0
        if not dry_run and job_ids:
            deleted_ids = tuple(
                self._session.scalars(
                    delete(Job).where(Job.id.in_(job_ids)).returning(Job.id)
                )
            )
            deleted_jobs = len(deleted_ids)
            if deleted_jobs != len(job_ids):
                raise RuntimeError("retention delete count changed inside transaction")

        return RetentionReport(
            dry_run=dry_run,
            candidate_jobs=len(job_ids),
            deleted_jobs=deleted_jobs,
            job_ids=job_ids,
            by_status=by_status,
        )


__all__ = ["JobRetention", "RetentionPolicy", "RetentionReport"]
