"""M41: lease recovery and unexpected failure handling on the worker path."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Chunk,
    ChunkSparseEmbedding,
    Document,
    DocumentVersion,
    Job,
    JobEvent,
    Project,
    Source,
)
from adaptive_rag.db.repositories import (
    JobRepository,
    ProjectRepository,
    SourceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.embeddings import (
    FakeDenseEmbeddingProvider,
    FakeSparseEmbeddingProvider,
)
from adaptive_rag.ingestion_ops import (
    enqueue_source_ingestion,
    get_ingestion_job_detail,
    run_next_ingestion_job,
)


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
            ChunkSparseEmbedding.__table__,
            Job.__table__,
            JobEvent.__table__,
        ],
    )
    return create_session_factory(engine)()


def _now() -> datetime:
    return datetime(2026, 8, 5, 15, 0, tzinfo=UTC)


def test_expired_running_job_is_released_and_reprocessed() -> None:
    """Kill mid-job simulation: expired lease must not stay running forever."""

    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="recover.md",
        extra_metadata={"content": "# Recover\n\nLease recovery requeues work."},
    )
    job = enqueue_source_ingestion(
        session,
        project_id=project.id,
        source_id=source.id,
    )
    # Simulate a worker that leased then died mid-job.
    job.status = "running"
    job.locked_by = "dead-worker"
    job.locked_until = _now() - timedelta(seconds=1)
    job.attempts = 1
    session.commit()

    report = run_next_ingestion_job(
        session,
        project_id=project.id,
        worker_id="recovery-worker",
        now=_now(),
        dense_embedding_provider=FakeDenseEmbeddingProvider(),
        sparse_embedding_provider=FakeSparseEmbeddingProvider(),
    )

    assert report.status == "processed"
    assert report.job_id == job.id
    stored = JobRepository(session).get(project_id=project.id, job_id=job.id)
    assert stored is not None
    assert stored.status == "succeeded"
    assert stored.locked_by is None

    events = [
        event.event_type
        for event in JobRepository(session).list_events(
            project_id=project.id,
            job_id=job.id,
        )
    ]
    assert "released" in events
    assert "leased" in events
    assert "completed" in events

    detail = get_ingestion_job_detail(
        session,
        project_id=project.id,
        job_id=job.id,
    )
    assert [event.event_type for event in detail.events] == events


def test_unexpected_error_fails_with_backoff_then_dead_letters() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="boom.md",
        extra_metadata={"content": "# Boom\n\nTransient failure."},
    )
    job = enqueue_source_ingestion(
        session,
        project_id=project.id,
        source_id=source.id,
        max_attempts=2,
    )
    session.commit()

    with patch(
        "adaptive_rag.ingestion_ops.IngestionPipeline.process_leased_job",
        side_effect=RuntimeError("disk full"),
    ):
        first = run_next_ingestion_job(
            session,
            project_id=project.id,
            worker_id="worker-1",
            now=_now(),
        )
        stored_after_first = JobRepository(session).get(
            project_id=project.id,
            job_id=job.id,
        )
        assert first.status == "failed"
        assert first.job_id == job.id
        assert first.error_message == "disk full"
        assert stored_after_first is not None
        assert stored_after_first.status == "queued"
        assert stored_after_first.locked_by is None
        assert stored_after_first.run_after > _now()
        assert stored_after_first.last_error == "disk full"

        second = run_next_ingestion_job(
            session,
            project_id=project.id,
            worker_id="worker-1",
            now=_now() + timedelta(seconds=2),
        )

    assert second.status == "dead_letter"
    stored_final = JobRepository(session).get(project_id=project.id, job_id=job.id)
    assert stored_final is not None
    assert stored_final.status == "dead_letter"
    assert stored_final.locked_by is None

    events = [
        event.event_type
        for event in JobRepository(session).list_events(
            project_id=project.id,
            job_id=job.id,
        )
    ]
    assert events.count("failed_attempt") == 1
    assert "dead_lettered" in events
    assert stored_final.status != "running"


def test_unexpected_error_after_failed_flush_still_fails_job() -> None:
    """A poisoned session (failed mid-pipeline flush) must not bypass fail()."""

    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="poison.md",
        extra_metadata={"content": "# Poison\n\nFlush failure."},
    )
    job = enqueue_source_ingestion(
        session,
        project_id=project.id,
        source_id=source.id,
    )
    session.commit()

    def poison_session(self, *, project_id, job):  # type: ignore[no-untyped-def]
        # Force a failed flush so the session needs a rollback, then raise an
        # unexpected error like a real mid-pipeline IntegrityError would.
        session.add(
            Job(
                id=job.id,
                project_id=project.id,
                job_type="ingest_source",
                run_after=_now(),
            )
        )
        try:
            session.flush()
        except Exception:
            pass
        raise RuntimeError("integrity blow-up")

    with patch(
        "adaptive_rag.ingestion_ops.IngestionPipeline.process_leased_job",
        poison_session,
    ):
        report = run_next_ingestion_job(
            session,
            project_id=project.id,
            worker_id="worker-1",
            now=_now(),
        )
    session.commit()

    assert report.status == "failed"
    assert report.job_id == job.id
    assert report.error_message == "integrity blow-up"

    stored = JobRepository(session).get(project_id=project.id, job_id=job.id)
    assert stored is not None
    assert stored.status == "queued"
    assert stored.locked_by is None
    assert stored.run_after > _now()
    assert stored.last_error == "integrity blow-up"

    events = [
        event.event_type
        for event in JobRepository(session).list_events(
            project_id=project.id,
            job_id=job.id,
        )
    ]
    assert "failed_attempt" in events


def test_run_next_calls_release_expired_leases_before_lease() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    session.commit()
    calls: list[tuple[object, object]] = []

    original_release = JobRepository.release_expired_leases
    original_lease = JobRepository.lease_next

    def tracking_release(self, *, project_id, now):  # type: ignore[no-untyped-def]
        calls.append(("release", now))
        return original_release(self, project_id=project_id, now=now)

    def tracking_lease(self, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(("lease", kwargs.get("now")))
        return original_lease(self, **kwargs)

    with (
        patch.object(JobRepository, "release_expired_leases", tracking_release),
        patch.object(JobRepository, "lease_next", tracking_lease),
    ):
        report = run_next_ingestion_job(
            session,
            project_id=project.id,
            worker_id="worker-1",
            now=_now(),
        )

    assert report.status == "idle"
    assert [name for name, _ in calls] == ["release", "lease"]
    assert calls[0][1] == _now()
    assert calls[1][1] == _now()
