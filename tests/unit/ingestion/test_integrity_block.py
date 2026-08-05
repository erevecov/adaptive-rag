"""Concurrent ingest IntegrityError becomes blocked, not uncaught."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Job, JobEvent, Project, Source
from adaptive_rag.db.repositories import ProjectRepository, SourceRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.ingestion.pipeline import IngestionBlockedResult, IngestionPipeline
from adaptive_rag.ingestion_ops import enqueue_source_ingestion


def test_process_leased_job_blocks_on_integrity_error(monkeypatch) -> None:
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            Source.__table__,
            Job.__table__,
            JobEvent.__table__,
        ],
    )
    session = create_session_factory(engine)()
    project = ProjectRepository(session).create(name="Demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="x.md",
        extra_metadata={"content": "# x"},
    )
    job = enqueue_source_ingestion(
        session,
        project_id=project.id,
        source_id=source.id,
    )
    session.commit()
    now = datetime.now(UTC)
    from adaptive_rag.db.repositories import JobRepository

    leased = JobRepository(session).lease_next(
        project_id=project.id,
        worker_id="w1",
        now=now,
        lease_until=now + timedelta(seconds=30),
        job_types=("ingest_source",),
    )
    assert leased is not None and leased.id == job.id
    session.commit()

    def boom(*, project_id, job):  # type: ignore[no-untyped-def]
        del project_id, job
        raise IntegrityError("stmt", {}, Exception("unique"))

    pipeline = IngestionPipeline(session)
    monkeypatch.setattr(pipeline, "_process_job", boom)
    result = pipeline.process_leased_job(project_id=project.id, job=leased)
    assert isinstance(result, IngestionBlockedResult)
    assert result.job.status == "blocked"
    assert "integrity" in result.error_message.lower()
