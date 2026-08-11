"""Timezone-aware cron expansion and replicated durable scheduling."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter
from sqlalchemy.orm import Session

from adaptive_rag.db.repositories.job_schedules import JobScheduleRepository
from adaptive_rag.jobs.registry import JobRegistry
from adaptive_rag.jobs.service import EnqueueJobRequest, JobService

MAX_OCCURRENCES_PER_TICK = 100


def validate_cron_schedule(
    *, expression: str, timezone: str, max_catch_up: int
) -> ZoneInfo:
    fields = expression.split()
    if len(fields) != 5 or expression.startswith("@"):
        raise ValueError("Only five-field cron expressions are supported")
    if not croniter.is_valid(expression):
        raise ValueError("Invalid cron expression")
    if not 1 <= max_catch_up <= MAX_OCCURRENCES_PER_TICK:
        raise ValueError("max_catch_up must be within [1, 100]")
    try:
        return ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown IANA timezone: {timezone}") from exc


def schedule_occurrences(
    *,
    expression: str,
    timezone: str,
    after_utc: datetime,
    through_utc: datetime,
    limit: int,
) -> list[datetime]:
    zone = validate_cron_schedule(
        expression=expression,
        timezone=timezone,
        max_catch_up=limit,
    )
    if after_utc.tzinfo is None or through_utc.tzinfo is None:
        raise ValueError("Cron range boundaries must be timezone-aware")
    after = after_utc.astimezone(UTC)
    through = through_utc.astimezone(UTC)
    if through <= after:
        return []

    base_local = after.astimezone(zone).replace(tzinfo=None)
    base_minute = base_local.replace(second=0, microsecond=0)
    local_candidates: list[datetime] = []
    if croniter.match(expression, base_minute):
        local_candidates.append(base_minute)
    iterator = croniter(expression, base_minute)
    results: set[datetime] = set()
    iterations = 0
    while len(results) < limit:
        if local_candidates:
            local_value = local_candidates.pop(0)
        else:
            local_value = iterator.get_next(datetime)
        iterations += 1
        if iterations > MAX_OCCURRENCES_PER_TICK:
            raise ValueError("Cron expansion exceeded 100 occurrences in one tick")
        resolved = _resolve_local_time(local_value, zone=zone)
        for instant in resolved:
            if after < instant <= through:
                results.add(instant)
        if resolved and min(resolved) > through:
            break
        if not resolved:
            # A nonexistent local minute can be beyond the UTC horizon only by
            # at most the offset transition. This guard avoids an extra day of
            # expansion while still allowing the next valid wall occurrence.
            local_horizon = through.astimezone(zone).replace(tzinfo=None)
            if local_value > local_horizon + timedelta(days=1):
                break
    return sorted(results)[:limit]


def apply_misfire_policy(
    occurrences: Sequence[datetime],
    policy: str,
    *,
    max_catch_up: int,
) -> list[datetime]:
    if not 1 <= max_catch_up <= MAX_OCCURRENCES_PER_TICK:
        raise ValueError("max_catch_up must be within [1, 100]")
    ordered = sorted(occurrences)
    if policy == "skip":
        return []
    if policy == "run_once":
        return ordered[-1:] if ordered else []
    if policy == "catch_up":
        return ordered[:max_catch_up]
    raise ValueError(f"Unknown misfire policy: {policy}")


def next_occurrence(*, expression: str, timezone: str, after_utc: datetime) -> datetime:
    horizon = after_utc.astimezone(UTC) + timedelta(days=366 * 8)
    values = schedule_occurrences(
        expression=expression,
        timezone=timezone,
        after_utc=after_utc,
        through_utc=horizon,
        limit=1,
    )
    if not values:
        raise ValueError("Cron expression produced no occurrence within eight years")
    return values[0]


def _resolve_local_time(value: datetime, *, zone: ZoneInfo) -> list[datetime]:
    instants: set[datetime] = set()
    for fold in (0, 1):
        aware = value.replace(tzinfo=zone, fold=fold)
        instant = aware.astimezone(UTC)
        round_trip = instant.astimezone(zone).replace(tzinfo=None)
        if round_trip == value:
            instants.add(instant)
    return sorted(instants)


class JobScheduler:
    """Expands locked due schedules into ordinary jobs in the caller transaction."""

    def __init__(self, *, session: Session, registry: JobRegistry) -> None:
        self._session = session
        self._registry = registry
        self._repository = JobScheduleRepository(session)

    def run_once(self, *, now: datetime, batch_size: int = 100) -> int:
        if not 1 <= batch_size <= MAX_OCCURRENCES_PER_TICK:
            raise ValueError("batch_size must be within [1, 100]")
        if now.tzinfo is None:
            raise ValueError("scheduler now must be timezone-aware")
        created = 0
        schedules = self._repository.lock_due(now=now, batch_size=batch_size)
        for schedule in schedules:
            due = schedule_occurrences(
                expression=schedule.cron_expression,
                timezone=schedule.timezone,
                after_utc=schedule.next_run_at - timedelta(minutes=1),
                through_utc=now,
                limit=MAX_OCCURRENCES_PER_TICK,
            )
            selected = apply_misfire_policy(
                due,
                schedule.misfire_policy,
                max_catch_up=schedule.max_catch_up,
            )
            service = JobService(session=self._session, registry=self._registry)
            for scheduled_for in selected:
                request = EnqueueJobRequest(
                    scope=schedule.scope,  # type: ignore[arg-type]
                    workspace_id=schedule.workspace_id,
                    job_type=schedule.job_type,
                    handler_version=schedule.handler_version,
                    payload=schedule.payload_json,
                    queue_name=schedule.queue_name,
                    priority=schedule.priority,
                    schedule_id=schedule.id,
                    scheduled_for=scheduled_for,
                    concurrency_key=schedule.concurrency_key,
                    run_after=scheduled_for,
                )
                if service.enqueue(request).created:
                    created += 1
            if due:
                schedule.last_scheduled_for = due[-1]
            schedule.next_run_at = next_occurrence(
                expression=schedule.cron_expression,
                timezone=schedule.timezone,
                after_utc=now,
            )
            schedule.version += 1
        self._session.flush()
        return created


__all__ = [
    "MAX_OCCURRENCES_PER_TICK",
    "JobScheduler",
    "apply_misfire_policy",
    "next_occurrence",
    "schedule_occurrences",
    "validate_cron_schedule",
]
