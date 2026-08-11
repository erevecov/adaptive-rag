"""Persistence primitives for durable cron schedules."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import JobSchedule


class JobScheduleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def lock_due(self, *, now: datetime, batch_size: int) -> list[JobSchedule]:
        return list(
            self._session.scalars(
                select(JobSchedule)
                .where(
                    JobSchedule.paused_at.is_(None),
                    JobSchedule.archived_at.is_(None),
                    JobSchedule.next_run_at <= now,
                )
                .order_by(JobSchedule.next_run_at, JobSchedule.id)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
        )

    def get_scoped(
        self,
        *,
        schedule_id: UUID,
        scope: str,
        workspace_id: UUID | None,
    ) -> JobSchedule | None:
        statement = select(JobSchedule).where(
            JobSchedule.id == schedule_id,
            JobSchedule.scope == scope,
        )
        if scope == "workspace":
            statement = statement.where(JobSchedule.workspace_id == workspace_id)
        else:
            statement = statement.where(JobSchedule.workspace_id.is_(None))
        return self._session.scalars(statement).one_or_none()


__all__ = ["JobScheduleRepository"]
