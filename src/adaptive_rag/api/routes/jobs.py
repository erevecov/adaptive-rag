"""Workspace and superadmin HTTP control plane for background jobs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from adaptive_rag.api.dependencies import (
    get_current_user,
    get_job_registry,
    get_session,
    get_superadmin_user,
    get_workspace_access,
    get_workspace_admin_access,
)
from adaptive_rag.api.schemas.jobs import (
    BackgroundJobResponse,
    ConfigureJobQueueBody,
    CreateJobScheduleBody,
    EnqueueJobBody,
    EnqueueJobResponse,
    JobDetailResponse,
    JobHandlerResponse,
    JobPageResponse,
    JobQueueResponse,
    JobScheduleListResponse,
    JobScheduleResponse,
    JobWorkerResponse,
    UpdateJobScheduleBody,
    VersionMutationBody,
)
from adaptive_rag.auth import CurrentPrincipal, role_meets
from adaptive_rag.db.models import Workspace
from adaptive_rag.jobs.errors import (
    JobIdempotencyConflictError,
    JobNotFoundError,
    JobPlatformError,
    JobQueueNotFoundError,
    JobStateConflictError,
    UnknownJobHandlerError,
)
from adaptive_rag.jobs.metrics import JobMetricsService
from adaptive_rag.jobs.registry import JobHandlerDefinition, JobRegistry
from adaptive_rag.jobs.schedule_service import (
    CreateJobScheduleRequest,
    JobScheduleService,
)
from adaptive_rag.jobs.service import EnqueueJobRequest, JobActor, JobService

router = APIRouter(tags=["background-jobs"])
admin_router = APIRouter(
    prefix="/admin",
    tags=["background-job-admin"],
    dependencies=[Depends(get_superadmin_user)],
)


@router.get(
    "/workspaces/{workspace_id}/job-handlers",
    response_model=list[JobHandlerResponse],
)
def list_workspace_job_handlers(
    workspace_id: UUID,
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> list[JobHandlerResponse]:
    role = _access[1]
    return [
        _handler_response(definition)
        for definition in registry.manual_definitions(minimum_role=role)
        if "workspace" in definition.allowed_scopes
    ]


@router.get(
    "/workspaces/{workspace_id}/jobs",
    response_model=JobPageResponse,
)
def list_workspace_jobs(
    workspace_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
    job_status: Annotated[str | None, Query(alias="status")] = None,
    queue_name: Annotated[str | None, Query(alias="queue")] = None,
    job_type: str | None = None,
) -> JobPageResponse:
    page = JobService(session=session, registry=registry).list_jobs(
        scope="workspace",
        workspace_id=workspace_id,
        limit=limit,
        cursor=cursor,
        status=job_status,
        queue_name=queue_name,
        job_type=job_type,
    )
    return JobPageResponse.from_page(page)


@router.post(
    "/workspaces/{workspace_id}/jobs",
    response_model=EnqueueJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def enqueue_workspace_job(
    workspace_id: UUID,
    body: EnqueueJobBody,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    access: Annotated[tuple[Workspace, str], Depends(get_workspace_admin_access)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> EnqueueJobResponse:
    try:
        definition = registry.get(body.job_type, body.handler_version)
        _require_manual_workspace_handler(definition=definition, role=access[1])
        result = JobService(session=session, registry=registry).enqueue(
            EnqueueJobRequest.workspace(
                workspace_id=workspace_id,
                job_type=body.job_type,
                handler_version=body.handler_version,
                payload=body.payload,
                queue_name=body.queue_name,
                priority=body.priority,
                idempotency_key=body.idempotency_key,
                run_after=body.run_after,
                concurrency_key=body.concurrency_key,
            )
        )
        session.commit()
    except Exception as exc:
        raise _job_http_error(exc) from exc
    if not result.created:
        response.status_code = status.HTTP_200_OK
    service = JobService(session=session, registry=registry)
    return EnqueueJobResponse(
        created=result.created,
        job=BackgroundJobResponse.from_snapshot(service.snapshot(result.job)),
    )


@router.get(
    "/workspaces/{workspace_id}/jobs/{job_id}",
    response_model=JobDetailResponse,
)
def get_workspace_job(
    workspace_id: UUID,
    job_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> JobDetailResponse:
    try:
        detail = JobService(session=session, registry=registry).get_detail(
            scope="workspace", workspace_id=workspace_id, job_id=job_id
        )
    except Exception as exc:
        raise _job_http_error(exc) from exc
    return JobDetailResponse.from_detail(detail)


@router.post(
    "/workspaces/{workspace_id}/jobs/{job_id}/cancel",
    response_model=BackgroundJobResponse,
)
def cancel_workspace_job(
    workspace_id: UUID,
    job_id: UUID,
    body: VersionMutationBody,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_admin_access)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> BackgroundJobResponse:
    return _workspace_mutation(
        operation="cancel",
        session=session,
        registry=registry,
        workspace_id=workspace_id,
        job_id=job_id,
        body=body,
        actor=_actor(current),
    )


@router.post(
    "/workspaces/{workspace_id}/jobs/{job_id}/retry",
    response_model=BackgroundJobResponse,
)
def retry_workspace_job(
    workspace_id: UUID,
    job_id: UUID,
    body: VersionMutationBody,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_admin_access)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> BackgroundJobResponse:
    return _workspace_mutation(
        operation="retry",
        session=session,
        registry=registry,
        workspace_id=workspace_id,
        job_id=job_id,
        body=body,
        actor=_actor(current),
    )


@router.post(
    "/workspaces/{workspace_id}/jobs/{job_id}/unblock",
    response_model=BackgroundJobResponse,
)
def unblock_workspace_job(
    workspace_id: UUID,
    job_id: UUID,
    body: VersionMutationBody,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_admin_access)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> BackgroundJobResponse:
    return _workspace_mutation(
        operation="unblock",
        session=session,
        registry=registry,
        workspace_id=workspace_id,
        job_id=job_id,
        body=body,
        actor=_actor(current),
    )


@router.get(
    "/workspaces/{workspace_id}/job-schedules",
    response_model=JobScheduleListResponse,
)
def list_workspace_schedules(
    workspace_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> JobScheduleListResponse:
    schedules = JobScheduleService(session=session, registry=registry).list(
        scope="workspace", workspace_id=workspace_id
    )
    return JobScheduleListResponse(
        items=[JobScheduleResponse.model_validate(row) for row in schedules]
    )


@router.post(
    "/workspaces/{workspace_id}/job-schedules",
    response_model=JobScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace_schedule(
    workspace_id: UUID,
    body: CreateJobScheduleBody,
    session: Annotated[Session, Depends(get_session)],
    access: Annotated[tuple[Workspace, str], Depends(get_workspace_admin_access)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> JobScheduleResponse:
    try:
        definition = registry.get(body.job_type, body.handler_version)
        _require_manual_workspace_handler(definition=definition, role=access[1])
        schedule = JobScheduleService(session=session, registry=registry).create(
            CreateJobScheduleRequest(
                scope="workspace",
                workspace_id=workspace_id,
                name=body.name,
                description=body.description,
                job_type=body.job_type,
                handler_version=body.handler_version,
                payload=body.payload,
                queue_name=body.queue_name,
                priority=body.priority,
                concurrency_key=body.concurrency_key,
                cron_expression=body.cron_expression,
                timezone=body.timezone,
                misfire_policy=body.misfire_policy,
                max_catch_up=body.max_catch_up,
            ),
            actor=_actor(current),
        )
        session.commit()
    except Exception as exc:
        raise _job_http_error(exc) from exc
    return JobScheduleResponse.model_validate(schedule)


@router.get(
    "/workspaces/{workspace_id}/job-schedules/{schedule_id}",
    response_model=JobScheduleResponse,
)
def get_workspace_schedule(
    workspace_id: UUID,
    schedule_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> JobScheduleResponse:
    try:
        schedule = JobScheduleService(session=session, registry=registry).get(
            schedule_id=schedule_id,
            scope="workspace",
            workspace_id=workspace_id,
        )
    except Exception as exc:
        raise _job_http_error(exc) from exc
    return JobScheduleResponse.model_validate(schedule)


@router.patch(
    "/workspaces/{workspace_id}/job-schedules/{schedule_id}",
    response_model=JobScheduleResponse,
)
def update_workspace_schedule(
    workspace_id: UUID,
    schedule_id: UUID,
    body: UpdateJobScheduleBody,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_admin_access)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> JobScheduleResponse:
    try:
        schedule = JobScheduleService(session=session, registry=registry).update(
            schedule_id=schedule_id,
            scope="workspace",
            workspace_id=workspace_id,
            actor=_actor(current),
            expected_version=body.version,
            name=body.name,
            description=body.description,
            payload=body.payload,
            queue_name=body.queue_name,
            priority=body.priority,
            concurrency_key=body.concurrency_key,
            cron_expression=body.cron_expression,
            timezone=body.timezone,
            misfire_policy=body.misfire_policy,
            max_catch_up=body.max_catch_up,
        )
        session.commit()
    except Exception as exc:
        raise _job_http_error(exc) from exc
    return JobScheduleResponse.model_validate(schedule)


@router.delete(
    "/workspaces/{workspace_id}/job-schedules/{schedule_id}",
    response_model=JobScheduleResponse,
)
def archive_workspace_schedule(
    workspace_id: UUID,
    schedule_id: UUID,
    body: VersionMutationBody,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_admin_access)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> JobScheduleResponse:
    try:
        schedule = JobScheduleService(session=session, registry=registry).archive(
            schedule_id=schedule_id,
            scope="workspace",
            workspace_id=workspace_id,
            actor=_actor(current),
            expected_version=body.version,
        )
        session.commit()
    except Exception as exc:
        raise _job_http_error(exc) from exc
    return JobScheduleResponse.model_validate(schedule)


@router.post(
    "/workspaces/{workspace_id}/job-schedules/{schedule_id}/{action}",
    response_model=JobScheduleResponse | BackgroundJobResponse,
)
def mutate_workspace_schedule(
    workspace_id: UUID,
    schedule_id: UUID,
    action: str,
    body: VersionMutationBody,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_admin_access)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> JobScheduleResponse | BackgroundJobResponse:
    service = JobScheduleService(session=session, registry=registry)
    actor = _actor(current)
    try:
        if action == "pause":
            result = service.pause(
                schedule_id=schedule_id,
                scope="workspace",
                workspace_id=workspace_id,
                actor=actor,
                expected_version=body.version,
            )
        elif action == "resume":
            result = service.resume(
                schedule_id=schedule_id,
                scope="workspace",
                workspace_id=workspace_id,
                actor=actor,
                expected_version=body.version,
            )
        elif action == "run-now":
            job = service.run_now(
                schedule_id=schedule_id,
                scope="workspace",
                workspace_id=workspace_id,
                actor=actor,
                expected_version=body.version,
            )
            session.commit()
            response.status_code = status.HTTP_201_CREATED
            snapshot = JobService(session=session, registry=registry).snapshot(job)
            return BackgroundJobResponse.from_snapshot(snapshot)
        else:
            raise HTTPException(status_code=404, detail="schedule action not found")
        session.commit()
    except HTTPException:
        raise
    except Exception as exc:
        raise _job_http_error(exc) from exc
    return JobScheduleResponse.model_validate(result)


@admin_router.get("/jobs", response_model=JobPageResponse)
def list_admin_jobs(
    session: Annotated[Session, Depends(get_session)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
    scope: str = "system",
    workspace_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
    job_status: Annotated[str | None, Query(alias="status")] = None,
    queue_name: Annotated[str | None, Query(alias="queue")] = None,
    job_type: str | None = None,
) -> JobPageResponse:
    if scope not in {"workspace", "system"}:
        raise HTTPException(status_code=422, detail="invalid job scope")
    if scope == "workspace" and workspace_id is None:
        raise HTTPException(status_code=422, detail="workspace_id is required")
    page = JobService(session=session, registry=registry).list_jobs(
        scope=scope,  # type: ignore[arg-type]
        workspace_id=workspace_id,
        limit=limit,
        cursor=cursor,
        status=job_status,
        queue_name=queue_name,
        job_type=job_type,
    )
    return JobPageResponse.from_page(page)


@admin_router.get("/job-handlers", response_model=list[JobHandlerResponse])
def list_admin_handlers(
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> list[JobHandlerResponse]:
    return [
        _handler_response(registry.get(*key))
        for key in sorted(registry.supported_handlers)
    ]


@admin_router.get("/job-queues", response_model=list[JobQueueResponse])
def list_admin_queues(
    session: Annotated[Session, Depends(get_session)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> list[JobQueueResponse]:
    return [
        JobQueueResponse.model_validate(row)
        for row in JobService(session=session, registry=registry).list_queues()
    ]


@admin_router.patch("/job-queues/{queue_name}", response_model=JobQueueResponse)
def configure_admin_queue(
    queue_name: str,
    body: ConfigureJobQueueBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> JobQueueResponse:
    try:
        queue = JobService(session=session, registry=registry).configure_queue(
            queue_name=queue_name,
            actor=_actor(current),
            expected_version=body.version,
            paused=body.paused,
            global_concurrency_limit=body.global_concurrency_limit,
            workspace_concurrency_limit=body.workspace_concurrency_limit,
            default_lease_seconds=body.default_lease_seconds,
        )
        session.commit()
    except Exception as exc:
        raise _job_http_error(exc) from exc
    return JobQueueResponse.model_validate(queue)


@admin_router.get("/job-queues/{queue_name}", response_model=JobQueueResponse)
def get_admin_queue(
    queue_name: str,
    session: Annotated[Session, Depends(get_session)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> JobQueueResponse:
    try:
        queue = JobService(session=session, registry=registry).get_queue(queue_name)
    except Exception as exc:
        raise _job_http_error(exc) from exc
    return JobQueueResponse.model_validate(queue)


@admin_router.get("/job-workers", response_model=list[JobWorkerResponse])
def list_admin_workers(
    session: Annotated[Session, Depends(get_session)],
    registry: Annotated[JobRegistry, Depends(get_job_registry)],
) -> list[JobWorkerResponse]:
    return [
        JobWorkerResponse.model_validate(row)
        for row in JobService(session=session, registry=registry).list_workers()
    ]


@admin_router.get("/job-metrics")
def get_admin_job_metrics(
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, object]:
    return JobMetricsService(session=session).snapshot(now=datetime.now(UTC))


def _workspace_mutation(
    *,
    operation: str,
    session: Session,
    registry: JobRegistry,
    workspace_id: UUID,
    job_id: UUID,
    body: VersionMutationBody,
    actor: JobActor,
) -> BackgroundJobResponse:
    service = JobService(session=session, registry=registry)
    try:
        if operation == "cancel":
            snapshot = service.cancel(
                scope="workspace",
                workspace_id=workspace_id,
                job_id=job_id,
                actor=actor,
                expected_version=body.version,
            )
        elif operation == "retry":
            snapshot = service.retry(
                scope="workspace",
                workspace_id=workspace_id,
                job_id=job_id,
                actor=actor,
                expected_version=body.version,
                reset_retry_count=body.reset_retry_count,
            )
        else:
            snapshot = service.unblock(
                scope="workspace",
                workspace_id=workspace_id,
                job_id=job_id,
                actor=actor,
                expected_version=body.version,
            )
        session.commit()
    except Exception as exc:
        raise _job_http_error(exc) from exc
    return BackgroundJobResponse.from_snapshot(snapshot)


def _require_manual_workspace_handler(
    *, definition: JobHandlerDefinition, role: str
) -> None:
    if (
        not definition.allow_manual_enqueue
        or "workspace" not in definition.allowed_scopes
        or not role_meets(role, definition.minimum_manual_role)
    ):
        raise HTTPException(
            status_code=403,
            detail="handler is not available for manual workspace enqueue",
        )


def _handler_response(definition: JobHandlerDefinition) -> JobHandlerResponse:
    return JobHandlerResponse(
        name=definition.name,
        version=definition.version,
        queue_name=definition.queue_name,
        allowed_scopes=sorted(definition.allowed_scopes),
        allow_manual_enqueue=definition.allow_manual_enqueue,
        minimum_manual_role=definition.minimum_manual_role,
    )


def _actor(current: CurrentPrincipal) -> JobActor:
    return JobActor(
        actor_type="user" if current.user_id is not None else "bootstrap",
        actor_id=str(current.user_id) if current.user_id is not None else "bootstrap",
    )


def _job_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (JobIdempotencyConflictError, JobStateConflictError)):
        return HTTPException(
            status_code=409,
            detail={"code": exc.code, "message": str(exc)},
        )
    if isinstance(exc, JobNotFoundError):
        return HTTPException(
            status_code=404,
            detail={"code": exc.code, "message": str(exc)},
        )
    if isinstance(
        exc,
        (
            UnknownJobHandlerError,
            JobQueueNotFoundError,
            ValidationError,
            ValueError,
        ),
    ):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, JobPlatformError):
        return HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": str(exc)},
        )
    return HTTPException(status_code=500, detail="background job operation failed")


__all__ = ["admin_router", "router"]
