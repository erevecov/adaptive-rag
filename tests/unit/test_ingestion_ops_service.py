from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Job, JobEvent, Project, Source
from adaptive_rag.db.repositories import (
    JobRepository,
    ProjectRepository,
    SourceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.ingestion.pipeline import INGEST_SOURCE_JOB_TYPE
from adaptive_rag.ingestion_ops import (
    IngestionOpsError,
    enqueue_source_ingestion,
    get_ingestion_job_detail,
    list_ingestion_jobs,
    retry_ingestion_job,
)


def test_enqueue_source_ingestion_creates_project_scoped_job() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="notes.md",
        extra_metadata={"content": "# Notes"},
    )

    job = enqueue_source_ingestion(
        session,
        project_id=project.id,
        source_id=source.id,
        priority=5,
        max_attempts=2,
    )

    assert job.project_id == project.id
    assert job.job_type == INGEST_SOURCE_JOB_TYPE
    assert job.status == "queued"
    assert job.priority == 5
    assert job.max_attempts == 2
    assert job.payload_json == {"source_id": str(source.id)}
    assert (
        JobRepository(session)
        .list_events(
            project_id=project.id,
            job_id=job.id,
        )[0]
        .event_type
        == "created"
    )


def test_enqueue_source_ingestion_dedupes_open_job_for_same_source() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="notes.md",
        extra_metadata={"content": "# Notes"},
    )

    first = enqueue_source_ingestion(
        session,
        project_id=project.id,
        source_id=source.id,
        priority=1,
    )
    second = enqueue_source_ingestion(
        session,
        project_id=project.id,
        source_id=source.id,
        priority=9,
    )

    assert second.id == first.id
    assert second.priority == 1
    open_jobs = JobRepository(session).list(
        project_id=project.id,
        job_type=INGEST_SOURCE_JOB_TYPE,
        statuses=("queued", "running"),
    )
    assert [job.id for job in open_jobs] == [first.id]


def test_enqueue_source_ingestion_allows_new_job_after_terminal_status() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="txt",
        external_id="notes.txt",
        extra_metadata={"content": "notes"},
    )
    first = enqueue_source_ingestion(
        session,
        project_id=project.id,
        source_id=source.id,
    )
    JobRepository(session).block(
        project_id=project.id,
        job_id=first.id,
        reason="blocked for test",
    )

    second = enqueue_source_ingestion(
        session,
        project_id=project.id,
        source_id=source.id,
    )

    assert second.id != first.id
    assert second.status == "queued"
    assert (
        JobRepository(session)
        .get(
            project_id=project.id,
            job_id=first.id,
        )
        .status
        == "blocked"
    )


def test_enqueue_source_ingestion_dedupes_running_job() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="txt",
        external_id="notes.txt",
        extra_metadata={"content": "notes"},
    )
    first = enqueue_source_ingestion(
        session,
        project_id=project.id,
        source_id=source.id,
    )
    # Lease clock must be >= run_after (enqueue uses wall-clock now).
    now = first.run_after
    from datetime import timedelta

    leased = JobRepository(session).lease_next(
        project_id=project.id,
        worker_id="worker-1",
        lease_until=now + timedelta(minutes=5),
        now=now,
        job_type=INGEST_SOURCE_JOB_TYPE,
    )
    assert leased is not None
    assert leased.id == first.id
    assert leased.status == "running"

    second = enqueue_source_ingestion(
        session,
        project_id=project.id,
        source_id=source.id,
    )

    assert second.id == first.id
    assert second.status == "running"


def test_enqueue_source_ingestion_rejects_cross_project_source() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    other_project = ProjectRepository(session).create(name="other")
    source = SourceRepository(session).create(
        project_id=other_project.id,
        source_type="txt",
        external_id="other.txt",
        extra_metadata={"content": "other"},
    )

    with pytest.raises(IngestionOpsError) as exc_info:
        enqueue_source_ingestion(
            session,
            project_id=project.id,
            source_id=source.id,
        )

    assert exc_info.value.detail == "source not found"
    assert exc_info.value.status_code == 404


def test_list_ingestion_jobs_filters_by_source_id() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source_a = SourceRepository(session).create(
        project_id=project.id,
        source_type="txt",
        external_id="a.txt",
        extra_metadata={"content": "a"},
    )
    source_b = SourceRepository(session).create(
        project_id=project.id,
        source_type="txt",
        external_id="b.txt",
        extra_metadata={"content": "b"},
    )
    job_a = enqueue_source_ingestion(
        session,
        project_id=project.id,
        source_id=source_a.id,
    )
    enqueue_source_ingestion(session, project_id=project.id, source_id=source_b.id)
    JobRepository(session).create(project_id=project.id, job_type="graph_backfill")

    jobs = list_ingestion_jobs(
        session,
        project_id=project.id,
        source_id=source_a.id,
        job_type=INGEST_SOURCE_JOB_TYPE,
    )

    assert [job.id for job in jobs] == [job_a.id]


def test_get_ingestion_job_detail_includes_events() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="txt",
        external_id="notes.txt",
        extra_metadata={"content": "notes"},
    )
    job = enqueue_source_ingestion(session, project_id=project.id, source_id=source.id)

    detail = get_ingestion_job_detail(
        session,
        project_id=project.id,
        job_id=job.id,
    )

    assert detail.job.id == job.id
    assert [event.event_type for event in detail.events] == ["created"]


def test_retry_ingestion_job_requeues_blocked_job() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="txt",
        external_id="notes.txt",
        extra_metadata={"content": "notes"},
    )
    job = enqueue_source_ingestion(session, project_id=project.id, source_id=source.id)
    JobRepository(session).block(project_id=project.id, job_id=job.id, reason="blocked")

    retried = retry_ingestion_job(
        session,
        project_id=project.id,
        job_id=job.id,
        run_after=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
    )

    assert retried.status == "queued"
    assert retried.last_error is None
    assert [
        event.event_type
        for event in JobRepository(session).list_events(
            project_id=project.id,
            job_id=job.id,
        )
    ] == ["created", "blocked", "retried"]


def test_retry_ingestion_job_returns_stable_errors() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="txt",
        external_id="notes.txt",
        extra_metadata={"content": "notes"},
    )
    job = enqueue_source_ingestion(session, project_id=project.id, source_id=source.id)

    with pytest.raises(IngestionOpsError) as missing:
        retry_ingestion_job(session, project_id=project.id, job_id=uuid4())

    with pytest.raises(IngestionOpsError) as non_retryable:
        retry_ingestion_job(session, project_id=project.id, job_id=job.id)

    assert missing.value.detail == "job not found"
    assert missing.value.status_code == 404
    assert non_retryable.value.detail == "job is not retryable"
    assert non_retryable.value.status_code == 409


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Project.__table__, Source.__table__, Job.__table__, JobEvent.__table__],
    )
    return create_session_factory(engine)()
