"""M48 knowledge lifecycle: resync, sync status, dedup report."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from adaptive_rag import authoring, knowledge_lifecycle
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Document,
    DocumentVersion,
    Job,
    JobEvent,
    Project,
    Source,
)
from adaptive_rag.db.repositories import JobRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.ingestion.pipeline import IngestionPipeline


def _session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Job.__table__,
            JobEvent.__table__,
        ],
    )
    return create_session_factory(engine)()


def test_resync_enqueues_ingest_job() -> None:
    session = _session()
    project = authoring.create_project(session, name="Life")
    source = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id="a.md",
        extra_metadata={"content": "hello lifecycle"},
    )
    result = knowledge_lifecycle.resync_source(
        session, project_id=project.id, source_id=source.id
    )
    assert result.job.job_type == "ingest_source"
    jobs = JobRepository(session).list(project_id=project.id)
    assert len(jobs) == 1


def test_ingest_marks_sync_and_dedup_detects_shared_hash() -> None:
    session = _session()
    project = authoring.create_project(session, name="Dedup")
    content = "shared body for both sources"
    s1 = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id="one.md",
        extra_metadata={"content": content},
    )
    s2 = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id="two.md",
        extra_metadata={"content": content},
    )
    for source in (s1, s2):
        JobRepository(session).create(
            project_id=project.id,
            job_type="ingest_source",
            payload_json={"source_id": str(source.id)},
            run_after=datetime(2026, 8, 5, tzinfo=UTC),
        )
    session.commit()
    pipeline = IngestionPipeline(session)
    now = datetime(2026, 8, 5, tzinfo=UTC)
    for _ in range(2):
        result = pipeline.run_next(
            project_id=project.id,
            worker_id="w",
            now=now,
            lease_until=now + timedelta(minutes=5),
        )
        assert result is not None

    status = knowledge_lifecycle.get_source_sync_status(
        session, project_id=project.id, source_id=s1.id
    )
    assert status.status == "synced"
    assert status.latest_content_hash
    assert status.last_synced_at is not None

    report = knowledge_lifecycle.build_dedup_report(session, project_id=project.id)
    assert report.duplicate_group_count == 1
    assert report.duplicate_version_count == 2
    assert s1.id in report.groups[0].source_ids
    assert s2.id in report.groups[0].source_ids
