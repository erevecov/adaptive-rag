"""Bounded operational metrics for the PostgreSQL job platform."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.db.models import Job, JobAttempt, JobEvent, JobSchedule
from adaptive_rag.jobs.metrics import JobMetricsService

NOW = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)


def test_metrics_expose_timing_outcomes_and_fencing_counts(
    job_session_factory: sessionmaker[Session],
) -> None:
    with job_session_factory() as session:
        schedule = session.scalars(select(JobSchedule).limit(1)).one()
        job = Job(
            scope="system",
            workspace_id=None,
            queue_name="default",
            job_type="metrics_echo",
            status="succeeded",
            payload_json={},
            run_after=NOW - timedelta(seconds=20),
            retry_count=2,
            created_at=NOW - timedelta(seconds=20),
            updated_at=NOW - timedelta(seconds=5),
            finished_at=NOW - timedelta(seconds=5),
            schedule_id=schedule.id,
            scheduled_for=NOW - timedelta(minutes=2),
        )
        session.add(job)
        session.flush()
        attempt = JobAttempt(
            job_id=job.id,
            scope="system",
            workspace_id=None,
            attempt_number=1,
            worker_id=uuid4(),
            status="succeeded",
            started_at=NOW - timedelta(seconds=15),
            heartbeat_at=NOW - timedelta(seconds=5),
            lease_expires_at=NOW + timedelta(seconds=45),
            finished_at=NOW - timedelta(seconds=5),
        )
        session.add(attempt)
        session.add_all(
            [
                JobEvent(
                    scope="system",
                    workspace_id=None,
                    job_id=job.id,
                    event_type="expired",
                ),
                JobEvent(
                    scope="system",
                    workspace_id=None,
                    job_id=job.id,
                    event_type="fenced_write_rejected",
                ),
            ]
        )
        session.commit()

    with job_session_factory() as session:
        snapshot = JobMetricsService(session=session).snapshot(now=NOW)

    assert snapshot["timings"]["enqueue_to_start_seconds"] == {
        "count": 1,
        "max": 5.0,
        "p50": 5.0,
        "p95": 5.0,
    }
    assert snapshot["timings"]["execution_duration_seconds"] == {
        "count": 1,
        "max": 10.0,
        "p50": 10.0,
        "p95": 10.0,
    }
    assert snapshot["outcomes"]["retries"] == 2
    assert snapshot["outcomes"]["expired_leases"] == 1
    assert snapshot["outcomes"]["fenced_write_rejections"] == 1
    assert snapshot["scheduler_misfires"] == 1
