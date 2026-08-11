"""Validated CRUD and actions for durable job schedules."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Job, JobEvent, JobQueue, JobSchedule
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.repositories.job_schedules import JobScheduleRepository
from adaptive_rag.jobs.errors import (
    JobNotFoundError,
    JobQueueNotFoundError,
    JobStateConflictError,
)
from adaptive_rag.jobs.registry import JobRegistry
from adaptive_rag.jobs.scheduler import next_occurrence, validate_cron_schedule
from adaptive_rag.jobs.service import EnqueueJobRequest, JobActor, JobService
from adaptive_rag.jobs.types import JobScope


@dataclass(frozen=True, slots=True)
class CreateJobScheduleRequest:
    scope: JobScope
    workspace_id: UUID | None
    name: str
    job_type: str
    payload: Mapping[str, object] = field(default_factory=dict)
    handler_version: int = 1
    description: str | None = None
    queue_name: str | None = None
    priority: int | None = None
    concurrency_key: str | None = None
    cron_expression: str = "0 * * * *"
    timezone: str = "UTC"
    misfire_policy: str = "run_once"
    max_catch_up: int = 1


class JobScheduleService:
    def __init__(self, *, session: Session, registry: JobRegistry) -> None:
        self._session = session
        self._registry = registry
        self._repository = JobScheduleRepository(session)

    def create(
        self,
        request: CreateJobScheduleRequest,
        *,
        actor: JobActor,
        now: datetime | None = None,
    ) -> JobSchedule:
        operation_time = now or utc_now()
        self._validate_scope(scope=request.scope, workspace_id=request.workspace_id)
        if not request.name.strip() or len(request.name.encode("utf-8")) > 200:
            raise ValueError("Schedule name must be 1-200 UTF-8 bytes")
        definition = self._registry.get(request.job_type, request.handler_version)
        if not definition.allow_manual_enqueue:
            raise ValueError("Handler does not allow manual schedules")
        if request.scope not in definition.allowed_scopes:
            raise ValueError("Handler does not allow this schedule scope")
        payload = self._registry.validate_payload(
            request.job_type, request.handler_version, request.payload
        ).model_dump(mode="json")
        queue_name = request.queue_name or definition.queue_name
        if self._session.get(JobQueue, queue_name) is None:
            raise JobQueueNotFoundError(f"Unknown job queue: {queue_name}")
        priority = (
            definition.default_priority
            if request.priority is None
            else request.priority
        )
        if not -1000 <= priority <= 1000:
            raise ValueError("Schedule priority must be within [-1000, 1000]")
        if request.misfire_policy not in {"skip", "run_once", "catch_up"}:
            raise ValueError("Unknown misfire policy")
        validate_cron_schedule(
            expression=request.cron_expression,
            timezone=request.timezone,
            max_catch_up=request.max_catch_up,
        )
        schedule = JobSchedule(
            scope=request.scope,
            workspace_id=request.workspace_id,
            name=request.name.strip(),
            description=request.description,
            queue_name=queue_name,
            job_type=request.job_type,
            handler_version=request.handler_version,
            payload_json=payload,
            priority=priority,
            concurrency_key=request.concurrency_key,
            cron_expression=request.cron_expression,
            timezone=request.timezone,
            misfire_policy=request.misfire_policy,
            max_catch_up=request.max_catch_up,
            next_run_at=next_occurrence(
                expression=request.cron_expression,
                timezone=request.timezone,
                after_utc=operation_time,
            ),
            created_by_actor_type=actor.actor_type,
            created_by_actor_id=actor.actor_id,
            updated_by_actor_type=actor.actor_type,
            updated_by_actor_id=actor.actor_id,
        )
        self._session.add(schedule)
        self._session.flush()
        return schedule

    def list(self, *, scope: JobScope, workspace_id: UUID | None) -> list[JobSchedule]:
        self._validate_scope(scope=scope, workspace_id=workspace_id)
        statement = select(JobSchedule).where(JobSchedule.scope == scope)
        if scope == "workspace":
            statement = statement.where(JobSchedule.workspace_id == workspace_id)
        else:
            statement = statement.where(JobSchedule.workspace_id.is_(None))
        return list(
            self._session.scalars(
                statement.order_by(JobSchedule.created_at, JobSchedule.id)
            )
        )

    def get(
        self,
        *,
        schedule_id: UUID,
        scope: JobScope,
        workspace_id: UUID | None,
    ) -> JobSchedule:
        self._validate_scope(scope=scope, workspace_id=workspace_id)
        schedule = self._repository.get_scoped(
            schedule_id=schedule_id,
            scope=scope,
            workspace_id=workspace_id,
        )
        if schedule is None:
            raise JobNotFoundError(f"Schedule not found: {schedule_id}")
        return schedule

    def pause(
        self,
        *,
        schedule_id: UUID,
        scope: JobScope,
        workspace_id: UUID | None,
        actor: JobActor,
        expected_version: int,
        now: datetime | None = None,
    ) -> JobSchedule:
        schedule = self._action_target(
            schedule_id=schedule_id,
            scope=scope,
            workspace_id=workspace_id,
            expected_version=expected_version,
        )
        if schedule.paused_at is not None:
            raise JobStateConflictError("Schedule is already paused")
        schedule.paused_at = now or utc_now()
        self._touch(schedule=schedule, actor=actor)
        self._session.flush()
        return schedule

    def update(
        self,
        *,
        schedule_id: UUID,
        scope: JobScope,
        workspace_id: UUID | None,
        actor: JobActor,
        expected_version: int,
        name: str | None = None,
        description: str | None = None,
        payload: Mapping[str, object] | None = None,
        queue_name: str | None = None,
        priority: int | None = None,
        concurrency_key: str | None = None,
        cron_expression: str | None = None,
        timezone: str | None = None,
        misfire_policy: str | None = None,
        max_catch_up: int | None = None,
        now: datetime | None = None,
    ) -> JobSchedule:
        schedule = self._action_target(
            schedule_id=schedule_id,
            scope=scope,
            workspace_id=workspace_id,
            expected_version=expected_version,
        )
        if name is not None:
            schedule.name = name.strip()
        if description is not None:
            schedule.description = description
        if payload is not None:
            schedule.payload_json = self._registry.validate_payload(
                schedule.job_type,
                schedule.handler_version,
                payload,
            ).model_dump(mode="json")
        if queue_name is not None:
            if self._session.get(JobQueue, queue_name) is None:
                raise JobQueueNotFoundError(f"Unknown job queue: {queue_name}")
            schedule.queue_name = queue_name
        if priority is not None:
            schedule.priority = priority
        if concurrency_key is not None:
            schedule.concurrency_key = concurrency_key
        expression = cron_expression or schedule.cron_expression
        zone = timezone or schedule.timezone
        policy = misfire_policy or schedule.misfire_policy
        catch_up = max_catch_up or schedule.max_catch_up
        if policy not in {"skip", "run_once", "catch_up"}:
            raise ValueError("Unknown misfire policy")
        validate_cron_schedule(
            expression=expression,
            timezone=zone,
            max_catch_up=catch_up,
        )
        schedule.cron_expression = expression
        schedule.timezone = zone
        schedule.misfire_policy = policy
        schedule.max_catch_up = catch_up
        if cron_expression is not None or timezone is not None:
            schedule.next_run_at = next_occurrence(
                expression=expression,
                timezone=zone,
                after_utc=now or utc_now(),
            )
        self._touch(schedule=schedule, actor=actor)
        self._session.flush()
        return schedule

    def resume(
        self,
        *,
        schedule_id: UUID,
        scope: JobScope,
        workspace_id: UUID | None,
        actor: JobActor,
        expected_version: int,
    ) -> JobSchedule:
        schedule = self._action_target(
            schedule_id=schedule_id,
            scope=scope,
            workspace_id=workspace_id,
            expected_version=expected_version,
        )
        if schedule.paused_at is None:
            raise JobStateConflictError("Schedule is not paused")
        schedule.paused_at = None
        self._touch(schedule=schedule, actor=actor)
        self._session.flush()
        return schedule

    def archive(
        self,
        *,
        schedule_id: UUID,
        scope: JobScope,
        workspace_id: UUID | None,
        actor: JobActor,
        expected_version: int,
        now: datetime | None = None,
    ) -> JobSchedule:
        schedule = self._action_target(
            schedule_id=schedule_id,
            scope=scope,
            workspace_id=workspace_id,
            expected_version=expected_version,
        )
        schedule.archived_at = now or utc_now()
        self._touch(schedule=schedule, actor=actor)
        self._session.flush()
        return schedule

    def run_now(
        self,
        *,
        schedule_id: UUID,
        scope: JobScope,
        workspace_id: UUID | None,
        actor: JobActor,
        expected_version: int,
        now: datetime | None = None,
    ) -> Job:
        schedule = self._action_target(
            schedule_id=schedule_id,
            scope=scope,
            workspace_id=workspace_id,
            expected_version=expected_version,
        )
        job = (
            JobService(session=self._session, registry=self._registry)
            .enqueue(
                EnqueueJobRequest(
                    scope=scope,
                    workspace_id=workspace_id,
                    job_type=schedule.job_type,
                    handler_version=schedule.handler_version,
                    payload=schedule.payload_json,
                    queue_name=schedule.queue_name,
                    priority=schedule.priority,
                    schedule_id=schedule.id,
                    scheduled_for=None,
                    concurrency_key=schedule.concurrency_key,
                    run_after=now or utc_now(),
                )
            )
            .job
        )
        self._session.add(
            JobEvent(
                scope=job.scope,
                workspace_id=job.workspace_id,
                job_id=job.id,
                event_type="run_now",
                actor_type=actor.actor_type,
                actor_id=actor.actor_id,
            )
        )
        self._session.flush()
        return job

    def _action_target(
        self,
        *,
        schedule_id: UUID,
        scope: JobScope,
        workspace_id: UUID | None,
        expected_version: int,
    ) -> JobSchedule:
        self._validate_scope(scope=scope, workspace_id=workspace_id)
        schedule = self._repository.get_scoped(
            schedule_id=schedule_id,
            scope=scope,
            workspace_id=workspace_id,
        )
        if schedule is None:
            raise JobNotFoundError(f"Schedule not found: {schedule_id}")
        if schedule.archived_at is not None:
            raise JobStateConflictError("Schedule is archived")
        if schedule.version != expected_version:
            raise JobStateConflictError("Schedule version changed")
        return schedule

    @staticmethod
    def _touch(*, schedule: JobSchedule, actor: JobActor) -> None:
        schedule.updated_by_actor_type = actor.actor_type
        schedule.updated_by_actor_id = actor.actor_id
        schedule.version += 1

    @staticmethod
    def _validate_scope(*, scope: JobScope, workspace_id: UUID | None) -> None:
        if scope == "workspace" and workspace_id is None:
            raise ValueError("workspace scope requires workspace_id")
        if scope == "system" and workspace_id is not None:
            raise ValueError("system scope cannot have workspace_id")


__all__ = ["CreateJobScheduleRequest", "JobScheduleService"]
