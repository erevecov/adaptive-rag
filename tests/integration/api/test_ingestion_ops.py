from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import get_session
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Chunk,
    Document,
    DocumentVersion,
    Job,
    JobEvent,
    Project,
    Source,
)
from adaptive_rag.db.repositories import ProjectRepository, SourceRepository
from adaptive_rag.db.session import create_session_factory


def test_enqueue_ingestion_job_lists_and_shows_events() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="Demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="notes.md",
        extra_metadata={"content": "# Notes"},
    )
    session.commit()
    client = _client(session=session)

    created = client.post(
        f"/projects/{project.id}/sources/{source.id}/ingestion-jobs",
        json={"priority": 3, "max_attempts": 2},
    )

    assert created.status_code == 200
    job = created.json()
    assert job["project_id"] == str(project.id)
    assert job["job_type"] == "ingest_source"
    assert job["status"] == "queued"
    assert job["priority"] == 3
    assert job["max_attempts"] == 2
    assert job["payload_json"] == {"source_id": str(source.id)}

    listed = client.get(
        f"/projects/{project.id}/ingestion-jobs",
        params={"source_id": str(source.id), "job_type": "ingest_source"},
    )
    shown = client.get(f"/projects/{project.id}/ingestion-jobs/{job['id']}")

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [job["id"]]
    assert shown.status_code == 200
    assert shown.json()["job"]["id"] == job["id"]
    assert [event["event_type"] for event in shown.json()["events"]] == ["created"]


def test_run_next_processes_text_source_and_updates_job_state() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="Demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="txt",
        external_id="notes.txt",
        extra_metadata={"content": "Evidence"},
    )
    session.commit()
    client = _client(session=session)
    created = client.post(f"/projects/{project.id}/sources/{source.id}/ingestion-jobs")

    run = client.post(
        f"/projects/{project.id}/ingestion-jobs/run-next",
        json={"worker_id": "api-test", "lease_seconds": 60},
    )
    detail = client.get(
        f"/projects/{project.id}/ingestion-jobs/{created.json()['id']}"
    )
    version = session.scalars(select(DocumentVersion)).one()

    assert run.status_code == 200
    payload = run.json()
    assert payload["status"] == "processed"
    assert payload["job_id"] == created.json()["id"]
    assert payload["source_id"] == str(source.id)
    assert payload["document_version_id"] == str(version.id)
    assert payload["created_document_version"] is True
    assert detail.json()["job"]["status"] == "succeeded"
    assert version.normalized_text == "Evidence"


def test_run_next_reports_blocked_job_and_retry_requeues_it() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="Demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="missing.md",
    )
    session.commit()
    client = _client(session=session)
    created = client.post(f"/projects/{project.id}/sources/{source.id}/ingestion-jobs")

    blocked = client.post(
        f"/projects/{project.id}/ingestion-jobs/run-next",
        json={"worker_id": "api-test"},
    )
    retried = client.post(
        f"/projects/{project.id}/ingestion-jobs/{created.json()['id']}/retry"
    )
    detail = client.get(
        f"/projects/{project.id}/ingestion-jobs/{created.json()['id']}"
    )

    assert blocked.status_code == 200
    assert blocked.json()["status"] == "blocked"
    assert blocked.json()["job_id"] == created.json()["id"]
    assert (
        blocked.json()["error_message"]
        == "markdown source requires extra_metadata.content"
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "queued"
    assert retried.json()["last_error"] is None
    assert [event["event_type"] for event in detail.json()["events"]] == [
        "created",
        "leased",
        "blocked",
        "retried",
    ]


def test_ingestion_ops_return_stable_not_found_and_retry_errors() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="Demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="txt",
        external_id="notes.txt",
        extra_metadata={"content": "Evidence"},
    )
    session.commit()
    client = _client(session=session)
    created = client.post(f"/projects/{project.id}/sources/{source.id}/ingestion-jobs")

    missing_source = client.post(
        f"/projects/{project.id}/sources/{uuid4()}/ingestion-jobs"
    )
    missing_job = client.get(f"/projects/{project.id}/ingestion-jobs/{uuid4()}")
    non_retryable = client.post(
        f"/projects/{project.id}/ingestion-jobs/{created.json()['id']}/retry"
    )

    assert missing_source.status_code == 404
    assert missing_source.json()["detail"] == "source not found"
    assert missing_job.status_code == 404
    assert missing_job.json()["detail"] == "job not found"
    assert non_retryable.status_code == 409
    assert non_retryable.json()["detail"] == "job is not retryable"


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
            Job.__table__,
            JobEvent.__table__,
        ],
    )
    return create_session_factory(engine)()


def _client(*, session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)
