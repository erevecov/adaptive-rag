"""Tests para JobRepository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Job, JobEvent, Workspace
from adaptive_rag.db.repositories import JobRepository, WorkspaceRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine, tables=[Workspace.__table__, Job.__table__, JobEvent.__table__]
    )
    return create_session_factory(engine)()


def _make_workspace(session, name: str = "demo") -> Workspace:
    return WorkspaceRepository(session).create(name=name)


def _event_types(repo: JobRepository, workspace: Workspace, job: Job) -> list[str]:
    return [
        event.event_type
        for event in repo.list_events(workspace_id=workspace.id, job_id=job.id)
    ]


def test_create_job_flushes_without_committing_and_adds_created_event():
    session = _make_session()
    workspace = _make_workspace(session)
    repo = JobRepository(session)

    job = repo.create(
        workspace_id=workspace.id,
        job_type="ingest_url",
        payload_json={"url": "https://example.com"},
    )
    events = repo.list_events(workspace_id=workspace.id, job_id=job.id)

    assert job.id is not None
    assert job.status == "queued"
    assert [event.event_type for event in events] == ["created"]

    session.rollback()
    session.expunge_all()

    assert repo.get(workspace_id=workspace.id, job_id=job.id) is None


def test_lease_next_takes_highest_priority_available_job_for_workspace():
    session = _make_session()
    workspace = _make_workspace(session)
    other_workspace = _make_workspace(session, "other")
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    repo.create(
        workspace_id=workspace.id, job_type="ingest_url", priority=1, run_after=now
    )
    wanted = repo.create(
        workspace_id=workspace.id,
        job_type="ingest_url",
        priority=10,
        run_after=now,
    )
    repo.create(
        workspace_id=workspace.id,
        job_type="ingest_url",
        priority=20,
        run_after=now + timedelta(minutes=5),
    )
    repo.create(
        workspace_id=other_workspace.id,
        job_type="ingest_url",
        priority=99,
        run_after=now,
    )
    session.commit()

    leased = repo.lease_next(
        workspace_id=workspace.id,
        worker_id="worker-1",
        lease_until=now + timedelta(minutes=10),
        now=now,
    )

    assert leased is not None
    assert leased.id == wanted.id
    assert leased.status == "running"
    assert leased.locked_by == "worker-1"
    assert leased.attempts == 1
    assert _event_types(repo, workspace, wanted) == ["created", "leased"]


def test_lease_next_filters_by_job_types_family():
    session = _make_session()
    workspace = _make_workspace(session)
    repo = JobRepository(session)
    now = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
    graph_job = repo.create(
        workspace_id=workspace.id,
        job_type="graph_backfill",
        priority=100,
        run_after=now,
    )
    index_job = repo.create(
        workspace_id=workspace.id,
        job_type="index_document_version",
        priority=5,
        run_after=now,
    )
    ingest_job = repo.create(
        workspace_id=workspace.id,
        job_type="ingest_source",
        priority=1,
        run_after=now,
    )
    session.commit()

    leased = repo.lease_next(
        workspace_id=workspace.id,
        worker_id="worker-family",
        lease_until=now + timedelta(minutes=10),
        now=now,
        job_types=("ingest_source", "index_document_version"),
    )

    assert leased is not None
    assert leased.id == index_job.id
    assert leased.job_type == "index_document_version"
    assert repo.get(workspace_id=workspace.id, job_id=graph_job.id).status == "queued"
    assert repo.get(workspace_id=workspace.id, job_id=ingest_job.id).status == "queued"


def test_complete_marks_running_job_succeeded_and_clears_lease():
    session = _make_session()
    workspace = _make_workspace(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = repo.create(workspace_id=workspace.id, job_type="ingest_url", run_after=now)
    repo.lease_next(
        workspace_id=workspace.id,
        worker_id="worker-1",
        lease_until=now + timedelta(minutes=10),
        now=now,
    )

    completed = repo.complete(
        workspace_id=workspace.id, job_id=job.id, worker_id="worker-1"
    )

    assert completed.status == "succeeded"
    assert completed.locked_by is None
    assert completed.locked_until is None
    assert _event_types(repo, workspace, job) == [
        "created",
        "leased",
        "completed",
    ]


def test_fail_retries_until_max_attempts_then_dead_letters():
    session = _make_session()
    workspace = _make_workspace(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = repo.create(
        workspace_id=workspace.id,
        job_type="ingest_url",
        max_attempts=2,
        run_after=now,
    )
    repo.lease_next(
        workspace_id=workspace.id,
        worker_id="worker-1",
        lease_until=now + timedelta(minutes=10),
        now=now,
    )

    retry = repo.fail(
        workspace_id=workspace.id,
        job_id=job.id,
        error_message="temporary",
        retry_after=now + timedelta(minutes=1),
        worker_id="worker-1",
    )
    retry_status = retry.status
    retry_locked_by = retry.locked_by
    repo.lease_next(
        workspace_id=workspace.id,
        worker_id="worker-1",
        lease_until=now + timedelta(minutes=20),
        now=now + timedelta(minutes=1),
    )
    dead = repo.fail(
        workspace_id=workspace.id,
        job_id=job.id,
        error_message="permanent",
        retry_after=now + timedelta(minutes=2),
        worker_id="worker-1",
    )

    assert retry_status == "queued"
    assert retry_locked_by is None
    assert dead.status == "dead_letter"
    assert dead.locked_by is None
    assert dead.last_error == "permanent"
    assert _event_types(repo, workspace, job) == [
        "created",
        "leased",
        "failed_attempt",
        "leased",
        "dead_lettered",
    ]


def test_block_marks_job_blocked_and_clears_lease():
    session = _make_session()
    workspace = _make_workspace(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = repo.create(workspace_id=workspace.id, job_type="ingest_url", run_after=now)
    repo.lease_next(
        workspace_id=workspace.id,
        worker_id="worker-1",
        lease_until=now + timedelta(minutes=10),
        now=now,
    )

    blocked = repo.block(
        workspace_id=workspace.id,
        job_id=job.id,
        reason="quota",
        worker_id="worker-1",
    )

    assert blocked.status == "blocked"
    assert blocked.locked_by is None
    assert blocked.last_error == "quota"
    assert _event_types(repo, workspace, job) == [
        "created",
        "leased",
        "blocked",
    ]


def test_release_expired_leases_returns_running_jobs_to_queue():
    session = _make_session()
    workspace = _make_workspace(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = repo.create(workspace_id=workspace.id, job_type="ingest_url", run_after=now)
    repo.lease_next(
        workspace_id=workspace.id,
        worker_id="worker-1",
        lease_until=now + timedelta(minutes=5),
        now=now,
    )

    released = repo.release_expired_leases(
        workspace_id=workspace.id,
        now=now + timedelta(minutes=6),
    )

    assert released == 1
    assert repo.get(workspace_id=workspace.id, job_id=job.id).status == "queued"
    assert repo.get(workspace_id=workspace.id, job_id=job.id).locked_by is None
    assert _event_types(repo, workspace, job) == [
        "created",
        "leased",
        "released",
    ]


def test_events_are_scoped_by_workspace():
    session = _make_session()
    workspace = _make_workspace(session)
    other_workspace = _make_workspace(session, "other")
    repo = JobRepository(session)
    job = repo.create(workspace_id=workspace.id, job_type="ingest_url")
    session.commit()

    assert repo.list_events(workspace_id=other_workspace.id, job_id=job.id) == []


def test_list_jobs_is_workspace_scoped_deterministic_and_filterable():
    session = _make_session()
    workspace = _make_workspace(session)
    other_workspace = _make_workspace(session, "other")
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    older = repo.create(
        workspace_id=workspace.id,
        job_type="ingest_source",
        payload_json={"source_id": "source-a"},
        run_after=now,
    )
    newer = repo.create(
        workspace_id=workspace.id,
        job_type="graph_backfill",
        run_after=now + timedelta(minutes=1),
    )
    repo.block(workspace_id=workspace.id, job_id=newer.id, reason="blocked")
    repo.create(
        workspace_id=other_workspace.id,
        job_type="ingest_source",
        run_after=now,
    )
    session.commit()

    all_jobs = repo.list(workspace_id=workspace.id)
    blocked_jobs = repo.list(workspace_id=workspace.id, status="blocked")
    ingest_jobs = repo.list(workspace_id=workspace.id, job_type="ingest_source")

    assert [job.id for job in all_jobs] == [older.id, newer.id]
    assert [job.id for job in blocked_jobs] == [newer.id]
    assert [job.id for job in ingest_jobs] == [older.id]


def test_requeue_blocked_job_clears_error_and_appends_retry_event():
    session = _make_session()
    workspace = _make_workspace(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = repo.create(
        workspace_id=workspace.id, job_type="ingest_source", run_after=now
    )
    repo.block(workspace_id=workspace.id, job_id=job.id, reason="missing content")
    session.commit()

    retried = repo.requeue(
        workspace_id=workspace.id,
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
    assert _event_types(repo, workspace, job) == ["created", "blocked", "retried"]


def test_requeue_rejects_non_retryable_job_status():
    session = _make_session()
    workspace = _make_workspace(session)
    repo = JobRepository(session)
    job = repo.create(workspace_id=workspace.id, job_type="ingest_source")
    session.commit()

    try:
        repo.requeue(workspace_id=workspace.id, job_id=job.id)
    except ValueError as exc:
        assert str(exc) == "job is not retryable"
    else:
        raise AssertionError("expected non-retryable job to fail")


def test_release_expired_leases_dead_letters_when_attempts_exhausted():
    """Crashed workers must not requeue forever past max_attempts."""

    session = _make_session()
    workspace = _make_workspace(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = repo.create(
        workspace_id=workspace.id,
        job_type="ingest_url",
        max_attempts=2,
        run_after=now,
    )
    # First lease (attempts=1), expire, requeue.
    repo.lease_next(
        workspace_id=workspace.id,
        worker_id="worker-1",
        lease_until=now + timedelta(minutes=5),
        now=now,
    )
    released_first = repo.release_expired_leases(
        workspace_id=workspace.id,
        now=now + timedelta(minutes=6),
    )
    stored = repo.get(workspace_id=workspace.id, job_id=job.id)
    assert released_first == 1
    assert stored is not None
    assert stored.status == "queued"
    assert stored.attempts == 1

    # Second lease (attempts=2 == max), expire → dead_letter.
    repo.lease_next(
        workspace_id=workspace.id,
        worker_id="worker-2",
        lease_until=now + timedelta(minutes=15),
        now=now + timedelta(minutes=6),
    )
    released_second = repo.release_expired_leases(
        workspace_id=workspace.id,
        now=now + timedelta(minutes=16),
    )
    dead = repo.get(workspace_id=workspace.id, job_id=job.id)
    assert released_second == 1
    assert dead is not None
    assert dead.status == "dead_letter"
    assert dead.locked_by is None
    assert dead.locked_until is None
    assert dead.attempts == 2
    assert dead.last_error == "lease expired"
    events = _event_types(repo, workspace, job)
    assert events.count("released") == 2
    assert "dead_lettered" in events
    assert events[-1] == "dead_lettered"


def test_complete_rejects_stale_worker_when_lease_held_by_other():
    session = _make_session()
    workspace = _make_workspace(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = repo.create(workspace_id=workspace.id, job_type="ingest_url", run_after=now)
    repo.lease_next(
        workspace_id=workspace.id,
        worker_id="owner-worker",
        lease_until=now + timedelta(minutes=10),
        now=now,
    )

    try:
        repo.complete(
            workspace_id=workspace.id,
            job_id=job.id,
            worker_id="stale-worker",
        )
    except ValueError as exc:
        assert str(exc) == "job is locked by another worker"
    else:
        raise AssertionError("expected stale complete to fail")

    stored = repo.get(workspace_id=workspace.id, job_id=job.id)
    assert stored is not None
    assert stored.status == "running"
    assert stored.locked_by == "owner-worker"


def test_fail_rejects_stale_worker_when_lease_held_by_other():
    session = _make_session()
    workspace = _make_workspace(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = repo.create(workspace_id=workspace.id, job_type="ingest_url", run_after=now)
    repo.lease_next(
        workspace_id=workspace.id,
        worker_id="owner-worker",
        lease_until=now + timedelta(minutes=10),
        now=now,
    )

    try:
        repo.fail(
            workspace_id=workspace.id,
            job_id=job.id,
            error_message="stale fail",
            worker_id="stale-worker",
        )
    except ValueError as exc:
        assert str(exc) == "job is locked by another worker"
    else:
        raise AssertionError("expected stale fail to fail")

    stored = repo.get(workspace_id=workspace.id, job_id=job.id)
    assert stored is not None
    assert stored.status == "running"
    assert stored.locked_by == "owner-worker"
    assert stored.last_error is None


def test_block_rejects_stale_worker_when_lease_held_by_other():
    session = _make_session()
    workspace = _make_workspace(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = repo.create(workspace_id=workspace.id, job_type="ingest_url", run_after=now)
    repo.lease_next(
        workspace_id=workspace.id,
        worker_id="owner-worker",
        lease_until=now + timedelta(minutes=10),
        now=now,
    )

    try:
        repo.block(
            workspace_id=workspace.id,
            job_id=job.id,
            reason="stale block",
            worker_id="stale-worker",
        )
    except ValueError as exc:
        assert str(exc) == "job is locked by another worker"
    else:
        raise AssertionError("expected stale block to fail")

    stored = repo.get(workspace_id=workspace.id, job_id=job.id)
    assert stored is not None
    assert stored.status == "running"
    assert stored.locked_by == "owner-worker"


def test_complete_without_worker_id_rejected_while_locked():
    """Missing worker_id cannot flip a leased job (must pass owner)."""

    session = _make_session()
    workspace = _make_workspace(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    job = repo.create(workspace_id=workspace.id, job_type="ingest_url", run_after=now)
    repo.lease_next(
        workspace_id=workspace.id,
        worker_id="owner-worker",
        lease_until=now + timedelta(minutes=10),
        now=now,
    )

    try:
        repo.complete(workspace_id=workspace.id, job_id=job.id)
    except ValueError as exc:
        assert str(exc) == "job is locked by another worker"
    else:
        raise AssertionError("expected complete without owner to fail")


def test_complete_and_block_allowed_when_unlocked():
    """Admin / unlocked paths keep working without worker_id."""

    session = _make_session()
    workspace = _make_workspace(session)
    repo = JobRepository(session)
    now = datetime(2026, 6, 18, 20, 0, tzinfo=UTC)
    to_block = repo.create(
        workspace_id=workspace.id, job_type="ingest_url", run_after=now
    )
    to_complete = repo.create(
        workspace_id=workspace.id, job_type="ingest_url", run_after=now
    )
    session.commit()

    blocked = repo.block(
        workspace_id=workspace.id, job_id=to_block.id, reason="manual hold"
    )
    completed = repo.complete(workspace_id=workspace.id, job_id=to_complete.id)

    assert blocked.status == "blocked"
    assert blocked.locked_by is None
    assert completed.status == "succeeded"
    assert completed.locked_by is None


def test_find_open_ingest_source_returns_oldest_queued_or_running():
    session = _make_session()
    workspace = _make_workspace(session)
    other = _make_workspace(session, "other")
    repo = JobRepository(session)
    source_a = "11111111-1111-1111-1111-111111111111"
    source_b = "22222222-2222-2222-2222-222222222222"
    from uuid import UUID

    older = repo.create(
        workspace_id=workspace.id,
        job_type="ingest_source",
        payload_json={"source_id": source_a},
    )
    repo.create(
        workspace_id=workspace.id,
        job_type="ingest_source",
        payload_json={"source_id": source_b},
    )
    repo.create(
        workspace_id=other.id,
        job_type="ingest_source",
        payload_json={"source_id": source_a},
    )
    session.commit()

    found = repo.find_open_ingest_source(
        workspace_id=workspace.id,
        source_id=UUID(source_a),
    )
    assert found is not None
    assert found.id == older.id

    # Succeeded is not open
    repo.complete(workspace_id=workspace.id, job_id=older.id)
    assert (
        repo.find_open_ingest_source(
            workspace_id=workspace.id,
            source_id=UUID(source_a),
        )
        is None
    )

    # New queued job is found again
    newer = repo.create(
        workspace_id=workspace.id,
        job_type="ingest_source",
        payload_json={"source_id": source_a},
    )
    assert (
        repo.find_open_ingest_source(
            workspace_id=workspace.id,
            source_id=UUID(source_a),
        ).id
        == newer.id
    )
