"""Tests para JobRepository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Job, JobEvent, Project
from adaptive_rag.db.repositories import JobRepository, ProjectRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine, tables=[Project.__table__, Job.__table__, JobEvent.__table__]
    )
    return create_session_factory(engine)()


def _make_project(session, name: str = "demo") -> Project:
    return ProjectRepository(session).create(name=name)


def _event_types(repo: JobRepository, project: Project, job: Job) -> list[str]:
    return [
        event.event_type
        for event in repo.list_events(project_id=project.id, job_id=job.id)
    ]


def test_create_job_flushes_without_committing_and_adds_created_event():
    session = _make_session()
    project = _make_project(session)
    repo = JobRepository(session)

    job = repo.create(
        project_id=project.id,
        job_type="ingest_url",
        payload_json={"url": "https://example.com"},
    )
    events = repo.list_events(project_id=project.id, job_id=job.id)

    assert job.id is not None
    assert job.status == "queued"
    assert [event.event_type for event in events] == ["created"]

    session.rollback()
    session.expunge_all()

    assert repo.get(project_id=project.id, job_id=job.id) is None


def test_lease_next_takes_highest_priority_available_job_for_project():
    session = _make_session()
    project = _make_project(session)
    other_project = _make_project(session, "other")
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    repo.create(project_id=project.id, job_type="ingest_url", priority=1, run_after=now)
    wanted = repo.create(
        project_id=project.id,
        job_type="ingest_url",
        priority=10,
        run_after=now,
    )
    repo.create(
        project_id=project.id,
        job_type="ingest_url",
        priority=20,
        run_after=now + timedelta(minutes=5),
    )
    repo.create(
        project_id=other_project.id,
        job_type="ingest_url",
        priority=99,
        run_after=now,
    )
    session.commit()

    leased = repo.lease_next(
        project_id=project.id,
        worker_id="worker-1",
        lease_until=now + timedelta(minutes=10),
        now=now,
    )

    assert leased is not None
    assert leased.id == wanted.id
    assert leased.status == "running"
    assert leased.locked_by == "worker-1"
    assert leased.attempts == 1
    assert _event_types(repo, project, wanted) == ["created", "leased"]


def test_complete_marks_running_job_succeeded_and_clears_lease():
    session = _make_session()
    project = _make_project(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = repo.create(project_id=project.id, job_type="ingest_url", run_after=now)
    repo.lease_next(
        project_id=project.id,
        worker_id="worker-1",
        lease_until=now + timedelta(minutes=10),
        now=now,
    )

    completed = repo.complete(project_id=project.id, job_id=job.id)

    assert completed.status == "succeeded"
    assert completed.locked_by is None
    assert completed.locked_until is None
    assert _event_types(repo, project, job) == [
        "created",
        "leased",
        "completed",
    ]


def test_fail_retries_until_max_attempts_then_dead_letters():
    session = _make_session()
    project = _make_project(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = repo.create(
        project_id=project.id,
        job_type="ingest_url",
        max_attempts=2,
        run_after=now,
    )
    repo.lease_next(
        project_id=project.id,
        worker_id="worker-1",
        lease_until=now + timedelta(minutes=10),
        now=now,
    )

    retry = repo.fail(
        project_id=project.id,
        job_id=job.id,
        error_message="temporary",
        retry_after=now + timedelta(minutes=1),
    )
    retry_status = retry.status
    retry_locked_by = retry.locked_by
    repo.lease_next(
        project_id=project.id,
        worker_id="worker-1",
        lease_until=now + timedelta(minutes=20),
        now=now + timedelta(minutes=1),
    )
    dead = repo.fail(
        project_id=project.id,
        job_id=job.id,
        error_message="permanent",
        retry_after=now + timedelta(minutes=2),
    )

    assert retry_status == "queued"
    assert retry_locked_by is None
    assert dead.status == "dead_letter"
    assert dead.locked_by is None
    assert dead.last_error == "permanent"
    assert _event_types(repo, project, job) == [
        "created",
        "leased",
        "failed_attempt",
        "leased",
        "dead_lettered",
    ]


def test_block_marks_job_blocked_and_clears_lease():
    session = _make_session()
    project = _make_project(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = repo.create(project_id=project.id, job_type="ingest_url", run_after=now)
    repo.lease_next(
        project_id=project.id,
        worker_id="worker-1",
        lease_until=now + timedelta(minutes=10),
        now=now,
    )

    blocked = repo.block(project_id=project.id, job_id=job.id, reason="quota")

    assert blocked.status == "blocked"
    assert blocked.locked_by is None
    assert blocked.last_error == "quota"
    assert _event_types(repo, project, job) == [
        "created",
        "leased",
        "blocked",
    ]


def test_release_expired_leases_returns_running_jobs_to_queue():
    session = _make_session()
    project = _make_project(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = repo.create(project_id=project.id, job_type="ingest_url", run_after=now)
    repo.lease_next(
        project_id=project.id,
        worker_id="worker-1",
        lease_until=now + timedelta(minutes=5),
        now=now,
    )

    released = repo.release_expired_leases(
        project_id=project.id,
        now=now + timedelta(minutes=6),
    )

    assert released == 1
    assert repo.get(project_id=project.id, job_id=job.id).status == "queued"
    assert repo.get(project_id=project.id, job_id=job.id).locked_by is None
    assert _event_types(repo, project, job) == [
        "created",
        "leased",
        "released",
    ]


def test_events_are_scoped_by_project():
    session = _make_session()
    project = _make_project(session)
    other_project = _make_project(session, "other")
    repo = JobRepository(session)
    job = repo.create(project_id=project.id, job_type="ingest_url")
    session.commit()

    assert repo.list_events(project_id=other_project.id, job_id=job.id) == []


def test_list_jobs_is_project_scoped_deterministic_and_filterable():
    session = _make_session()
    project = _make_project(session)
    other_project = _make_project(session, "other")
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    older = repo.create(
        project_id=project.id,
        job_type="ingest_source",
        payload_json={"source_id": "source-a"},
        run_after=now,
    )
    newer = repo.create(
        project_id=project.id,
        job_type="graph_backfill",
        run_after=now + timedelta(minutes=1),
    )
    repo.block(project_id=project.id, job_id=newer.id, reason="blocked")
    repo.create(
        project_id=other_project.id,
        job_type="ingest_source",
        run_after=now,
    )
    session.commit()

    all_jobs = repo.list(project_id=project.id)
    blocked_jobs = repo.list(project_id=project.id, status="blocked")
    ingest_jobs = repo.list(project_id=project.id, job_type="ingest_source")

    assert [job.id for job in all_jobs] == [older.id, newer.id]
    assert [job.id for job in blocked_jobs] == [newer.id]
    assert [job.id for job in ingest_jobs] == [older.id]


def test_requeue_blocked_job_clears_error_and_appends_retry_event():
    session = _make_session()
    project = _make_project(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = repo.create(project_id=project.id, job_type="ingest_source", run_after=now)
    repo.block(project_id=project.id, job_id=job.id, reason="missing content")
    session.commit()

    retried = repo.requeue(
        project_id=project.id,
        job_id=job.id,
        run_after=now + timedelta(minutes=5),
        reset_attempts=True,
    )

    assert retried.status == "queued"
    assert retried.run_after == now + timedelta(minutes=5)
    assert retried.locked_by is None
    assert retried.locked_until is None
    assert retried.last_error is None
    assert retried.attempts == 0
    assert _event_types(repo, project, job) == ["created", "blocked", "retried"]


def test_requeue_rejects_non_retryable_job_status():
    session = _make_session()
    project = _make_project(session)
    repo = JobRepository(session)
    job = repo.create(project_id=project.id, job_type="ingest_source")
    session.commit()

    try:
        repo.requeue(project_id=project.id, job_id=job.id)
    except ValueError as exc:
        assert str(exc) == "job is not retryable"
    else:
        raise AssertionError("expected non-retryable job to fail")
