"""Transactional enqueue, idempotency, pagination, and redacted detail."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import BaseModel, ConfigDict

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Job,
    JobAttempt,
    JobEvent,
    JobQueue,
    JobQueueWorkspaceState,
    JobSchedule,
    JobWorker,
    Workspace,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.jobs import JobHandlerDefinition, JobRegistry
from adaptive_rag.jobs.service import (
    EnqueueJobRequest,
    JobIdempotencyConflictError,
    JobQueueNotFoundError,
    JobService,
)


class EchoPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


def _echo(_context, payload: EchoPayload) -> dict[str, str]:
    return {"echo": payload.message}


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Workspace.__table__,
            JobQueue.__table__,
            JobSchedule.__table__,
            Job.__table__,
            JobAttempt.__table__,
            JobEvent.__table__,
            JobQueueWorkspaceState.__table__,
            JobWorker.__table__,
        ],
    )
    session = create_session_factory(engine)()
    session.add_all([JobQueue(name="default"), JobQueue(name="system")])
    workspace = Workspace(name="demo")
    session.add(workspace)
    session.commit()
    return session, workspace


def _registry(*, redact_message: bool = False) -> JobRegistry:
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="echo",
            version=1,
            payload_model=EchoPayload,
            handler=_echo,
            queue_name="default",
            allowed_scopes=frozenset({"workspace", "system"}),
            redact_payload=(
                (lambda value: {"message": "[REDACTED]"})
                if redact_message
                else (lambda value: value)
            ),
        )
    )
    return registry


def test_enqueue_returns_existing_matching_open_job_without_committing() -> None:
    session, workspace = _make_session()
    service = JobService(session=session, registry=_registry())
    request = EnqueueJobRequest.workspace(
        workspace_id=workspace.id,
        job_type="echo",
        payload={"message": "hi"},
        idempotency_key="message-1",
    )

    first = service.enqueue(request)
    second = service.enqueue(request)

    assert first.created is True
    assert second.created is False
    assert second.job.id == first.job.id
    assert session.in_transaction() is True
    assert [event.event_type for event in session.query(JobEvent).all()] == [
        "created",
        "queued",
    ]

    job_id = first.job.id
    session.rollback()
    assert session.get(Job, job_id) is None


def test_same_key_with_different_payload_is_conflict() -> None:
    session, _workspace = _make_session()
    service = JobService(session=session, registry=_registry())
    service.enqueue(
        EnqueueJobRequest.system(
            job_type="echo",
            payload={"message": "one"},
            idempotency_key="same",
        )
    )

    with pytest.raises(JobIdempotencyConflictError):
        service.enqueue(
            EnqueueJobRequest.system(
                job_type="echo",
                payload={"message": "two"},
                idempotency_key="same",
            )
        )


def test_workspace_and_system_idempotency_keys_do_not_collide() -> None:
    session, workspace = _make_session()
    service = JobService(session=session, registry=_registry())

    workspace_job = service.enqueue(
        EnqueueJobRequest.workspace(
            workspace_id=workspace.id,
            job_type="echo",
            payload={"message": "same"},
            idempotency_key="daily",
        )
    )
    system_job = service.enqueue(
        EnqueueJobRequest.system(
            job_type="echo",
            payload={"message": "same"},
            idempotency_key="daily",
        )
    )

    assert workspace_job.job.id != system_job.job.id


def test_enqueue_rejects_an_unconfigured_queue() -> None:
    session, _workspace = _make_session()
    service = JobService(session=session, registry=_registry())

    with pytest.raises(JobQueueNotFoundError):
        service.enqueue(
            EnqueueJobRequest.system(
                job_type="echo",
                payload={"message": "hi"},
                queue_name="missing",
            )
        )


def test_cursor_pagination_is_stable_and_redacted_detail_is_detached() -> None:
    session, workspace = _make_session()
    service = JobService(session=session, registry=_registry(redact_message=True))
    base = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    job_ids = []
    for index in range(3):
        result = service.enqueue(
            EnqueueJobRequest.workspace(
                workspace_id=workspace.id,
                job_type="echo",
                payload={"message": f"message-{index}"},
                run_after=base + timedelta(minutes=index),
            )
        )
        result.job.created_at = base + timedelta(seconds=index)
        job_ids.append(result.job.id)
    session.commit()

    first = service.list_jobs(scope="workspace", workspace_id=workspace.id, limit=2)
    second = service.list_jobs(
        scope="workspace",
        workspace_id=workspace.id,
        limit=2,
        cursor=first.next_cursor,
    )
    detail = service.get_detail(
        scope="workspace", workspace_id=workspace.id, job_id=job_ids[0]
    )

    assert len(first.items) == 2
    assert first.next_cursor is not None
    assert len(second.items) == 1
    assert {item.id for item in first.items}.isdisjoint(
        {item.id for item in second.items}
    )
    assert detail.job.payload_json == {"message": "[REDACTED]"}
    assert session.get(Job, job_ids[0]).payload_json == {"message": "message-0"}
