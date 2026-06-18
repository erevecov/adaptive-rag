"""Tests para modelos Job y JobEvent."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Job, JobEvent, Project
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine, tables=[Project.__table__, Job.__table__, JobEvent.__table__]
    )
    return create_session_factory(engine)()


def _make_project(session) -> Project:
    project = Project(name="demo")
    session.add(project)
    session.commit()
    return project


def test_job_defaults_to_queued_with_retry_budget():
    session = _make_session()
    project = _make_project(session)
    job = Job(project_id=project.id, job_type="ingest_url")

    session.add(job)
    session.commit()

    assert job.status == "queued"
    assert job.attempts == 0
    assert job.max_attempts == 3
    assert job.priority == 0
    assert job.run_after is not None


def test_job_payload_and_lock_fields_persist():
    session = _make_session()
    project = _make_project(session)
    locked_until = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = Job(
        project_id=project.id,
        job_type="ingest_url",
        payload_json={"url": "https://example.com"},
        status="running",
        locked_by="worker-1",
        locked_until=locked_until,
    )

    session.add(job)
    session.commit()
    session.expunge_all()

    fetched = session.execute(select(Job).where(Job.id == job.id)).scalar_one()

    assert fetched.payload_json == {"url": "https://example.com"}
    assert fetched.locked_by == "worker-1"
    assert fetched.locked_until is not None


def test_job_rejects_invalid_status():
    session = _make_session()
    project = _make_project(session)
    job = Job(project_id=project.id, job_type="ingest_url", status="bogus")

    session.add(job)

    try:
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for invalid job status")


def test_job_attempts_and_max_attempts_have_constraints():
    columns = {c.name: c for c in inspect(Job).columns}
    constraints = {c.name for c in inspect(Job).local_table.constraints}

    assert columns["attempts"].nullable is False
    assert columns["max_attempts"].nullable is False
    assert "jobs_attempts_non_negative_check" in constraints
    assert "jobs_max_attempts_positive_check" in constraints


def test_job_project_status_and_lease_columns_are_indexed():
    table = inspect(Job).local_table
    indexed_columns: set[tuple[str, ...]] = {
        tuple(col.name for col in index.columns) for index in table.indexes
    }

    assert ("project_id", "status", "run_after", "priority") in indexed_columns
    assert ("project_id", "locked_until") in indexed_columns


def test_job_event_persists_event_audit_data():
    session = _make_session()
    project = _make_project(session)
    job = Job(project_id=project.id, job_type="ingest_url")
    session.add(job)
    session.flush()
    event = JobEvent(
        project_id=project.id,
        job_id=job.id,
        event_type="created",
        message="created job",
        extra_metadata={"source": "test"},
    )

    session.add(event)
    session.commit()
    session.expunge_all()

    fetched = session.execute(
        select(JobEvent).where(JobEvent.job_id == job.id)
    ).scalar_one()

    assert fetched.project_id == project.id
    assert fetched.event_type == "created"
    assert fetched.message == "created job"
    assert fetched.extra_metadata == {"source": "test"}


def test_job_event_rejects_invalid_event_type():
    session = _make_session()
    project = _make_project(session)
    job = Job(project_id=project.id, job_type="ingest_url")
    session.add(job)
    session.flush()
    event = JobEvent(project_id=project.id, job_id=job.id, event_type="bogus")
    session.add(event)

    try:
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for invalid event type")
