"""Transactional terminal-job retention on PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.db.models import Job, JobAttempt, JobEvent, ProviderUsage, Workspace
from adaptive_rag.jobs.retention import JobRetention, RetentionPolicy

NOW = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)


def test_retention_dry_run_is_bounded_and_does_not_mutate(
    job_session_factory: sessionmaker[Session],
) -> None:
    old_job_id, _attempt_id = _terminal_job(job_session_factory, status="succeeded")

    with job_session_factory() as session:
        report = JobRetention(session=session).run(
            policy=RetentionPolicy(succeeded_after=timedelta(days=30)),
            now=NOW,
            dry_run=True,
            batch_size=10,
        )
        session.commit()

    assert report.job_ids == (old_job_id,)
    assert report.deleted_jobs == 0
    assert report.candidate_jobs == 1
    with job_session_factory() as session:
        assert session.get(Job, old_job_id) is not None


def test_retention_deletes_history_atomically_and_preserves_audit_references(
    job_session_factory: sessionmaker[Session],
) -> None:
    deleted_job_id, deleted_attempt_id = _terminal_job(
        job_session_factory, status="cancelled"
    )
    protected_job_id, _ = _terminal_job(
        job_session_factory,
        status="succeeded",
        protect_with_provider_usage=True,
    )
    recent_job_id, _ = _terminal_job(
        job_session_factory,
        status="succeeded",
        age=timedelta(days=1),
    )
    blocked_job_id, _ = _terminal_job(job_session_factory, status="blocked")

    with job_session_factory() as session:
        report = JobRetention(session=session).run(
            policy=RetentionPolicy(
                cancelled_after=timedelta(days=30),
                succeeded_after=timedelta(days=30),
            ),
            now=NOW,
            dry_run=False,
            batch_size=100,
        )
        session.commit()

    assert report.job_ids == (deleted_job_id,)
    assert report.deleted_jobs == 1
    with job_session_factory() as session:
        assert session.get(Job, deleted_job_id) is None
        assert session.get(JobAttempt, deleted_attempt_id) is None
        assert (
            session.scalar(
                select(func.count(JobEvent.id)).where(
                    JobEvent.job_id == deleted_job_id
                )
            )
            == 0
        )
        assert session.get(Job, protected_job_id) is not None
        assert session.get(Job, recent_job_id) is not None
        assert session.get(Job, blocked_job_id) is not None


def _terminal_job(
    factory: sessionmaker[Session],
    *,
    status: str,
    age: timedelta = timedelta(days=60),
    protect_with_provider_usage: bool = False,
) -> tuple:
    with factory() as session:
        workspace = Workspace(name=f"retention-{uuid4()}")
        session.add(workspace)
        session.flush()
        finished_at = NOW - age if status != "blocked" else None
        job = Job(
            scope="workspace",
            workspace_id=workspace.id,
            queue_name="default",
            job_type="retention_test",
            status=status,
            payload_json={},
            run_after=NOW - age,
            finished_at=finished_at,
            created_at=NOW - age,
            updated_at=NOW - age,
        )
        session.add(job)
        session.flush()
        attempt = JobAttempt(
            job_id=job.id,
            scope="workspace",
            workspace_id=workspace.id,
            attempt_number=1,
            worker_id=uuid4(),
            status="succeeded" if status == "succeeded" else "cancelled",
            started_at=NOW - age,
            heartbeat_at=NOW - age,
            lease_expires_at=NOW - age + timedelta(minutes=5),
            finished_at=finished_at,
        )
        session.add(attempt)
        session.add(
            JobEvent(
                scope="workspace",
                workspace_id=workspace.id,
                job_id=job.id,
                attempt_id=attempt.id,
                event_type="completed",
            )
        )
        if protect_with_provider_usage:
            session.add(
                ProviderUsage(
                    workspace_id=workspace.id,
                    job_id=job.id,
                    operation="embedding",
                    provider="fake",
                    model="fake",
                    status="succeeded",
                    usage_source="unavailable",
                )
            )
        session.commit()
        return job.id, attempt.id
