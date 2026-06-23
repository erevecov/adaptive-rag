from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from typer.testing import CliRunner

from adaptive_rag.cli.app import app
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
from adaptive_rag.db.repositories import (
    JobRepository,
    ProjectRepository,
    SourceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def test_jobs_run_worker_command_is_registered() -> None:
    result = CliRunner().invoke(app, ["jobs", "--help"])

    assert result.exit_code == 0
    assert "enqueue-ingest-source" in result.stdout
    assert "list" in result.stdout
    assert "show" in result.stdout
    assert "retry" in result.stdout
    assert "run-worker" in result.stdout


def test_jobs_enqueue_list_and_show_ingestion_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="demo.md",
        extra_metadata={"content": "# Demo"},
    )
    session.commit()
    _patch_jobs_session_scope(monkeypatch, session=session)
    runner = CliRunner()

    created = runner.invoke(
        app,
        [
            "jobs",
            "enqueue-ingest-source",
            "--project-id",
            str(project.id),
            "--source-id",
            str(source.id),
            "--priority",
            "4",
        ],
    )

    assert created.exit_code == 0
    job = json.loads(created.stdout)
    assert job["job_type"] == "ingest_source"
    assert job["status"] == "queued"
    assert job["priority"] == 4
    assert job["payload_json"] == {"source_id": str(source.id)}

    listed = runner.invoke(
        app,
        [
            "jobs",
            "list",
            "--project-id",
            str(project.id),
            "--source-id",
            str(source.id),
        ],
    )
    shown = runner.invoke(
        app,
        [
            "jobs",
            "show",
            "--project-id",
            str(project.id),
            "--job-id",
            job["id"],
        ],
    )

    assert listed.exit_code == 0
    assert [item["id"] for item in json.loads(listed.stdout)["items"]] == [job["id"]]
    assert shown.exit_code == 0
    detail = json.loads(shown.stdout)
    assert detail["job"]["id"] == job["id"]
    assert [event["event_type"] for event in detail["events"]] == ["created"]


def test_jobs_retry_requeues_blocked_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    job = JobRepository(session).create(project_id=project.id, job_type="ingest_source")
    JobRepository(session).block(project_id=project.id, job_id=job.id, reason="blocked")
    session.commit()
    _patch_jobs_session_scope(monkeypatch, session=session)

    result = CliRunner().invoke(
        app,
        [
            "jobs",
            "retry",
            "--project-id",
            str(project.id),
            "--job-id",
            str(job.id),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "queued"
    assert payload["last_error"] is None


def test_jobs_commands_return_stable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    session.commit()
    _patch_jobs_session_scope(monkeypatch, session=session)
    runner = CliRunner()

    missing_source = runner.invoke(
        app,
        [
            "jobs",
            "enqueue-ingest-source",
            "--project-id",
            str(project.id),
            "--source-id",
            str(project.id),
        ],
    )
    missing_job = runner.invoke(
        app,
        [
            "jobs",
            "show",
            "--project-id",
            str(project.id),
            "--job-id",
            str(project.id),
        ],
    )

    assert missing_source.exit_code == 1
    assert missing_source.stderr.strip() == "source not found"
    assert missing_job.exit_code == 1
    assert missing_job.stderr.strip() == "job not found"


def test_jobs_run_worker_once_processes_ingest_source_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="demo.md",
        extra_metadata={"content": "# Demo\n\nEvidence"},
    )
    job = JobRepository(session).create(
        project_id=project.id,
        job_type="ingest_source",
        payload_json={"source_id": str(source.id)},
        run_after=datetime(2020, 1, 1, 12, 0, tzinfo=UTC),
    )
    session.commit()

    @contextmanager
    def override_session_scope() -> Iterator[object]:
        yield session

    monkeypatch.setattr("adaptive_rag.cli.jobs.session_scope", override_session_scope)

    result = CliRunner().invoke(
        app,
        [
            "jobs",
            "run-worker",
            "--project-id",
            str(project.id),
            "--worker-id",
            "worker-test",
            "--once",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "processed"
    assert payload["processed_jobs"] == 1
    assert payload["job_id"] == str(job.id)
    assert payload["created_document_version"] is True

    stored_job = JobRepository(session).get(project_id=project.id, job_id=job.id)
    document_version = session.scalars(select(DocumentVersion)).one()
    assert stored_job is not None
    assert stored_job.status == "succeeded"
    assert document_version.normalized_text == "# Demo\n\nEvidence"


def test_jobs_run_worker_once_reports_blocked_ingestion_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="missing.md",
    )
    job = JobRepository(session).create(
        project_id=project.id,
        job_type="ingest_source",
        payload_json={"source_id": str(source.id)},
        run_after=datetime(2020, 1, 1, 12, 0, tzinfo=UTC),
    )
    session.commit()

    @contextmanager
    def override_session_scope() -> Iterator[object]:
        yield session

    monkeypatch.setattr("adaptive_rag.cli.jobs.session_scope", override_session_scope)

    result = CliRunner().invoke(
        app,
        [
            "jobs",
            "run-worker",
            "--project-id",
            str(project.id),
            "--worker-id",
            "worker-test",
            "--once",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "blocked"
    assert payload["job_id"] == str(job.id)
    assert payload["source_id"] == str(source.id)
    assert payload["error_message"] == "markdown source requires extra_metadata.content"

    stored_job = JobRepository(session).get(project_id=project.id, job_id=job.id)
    assert stored_job is not None
    assert stored_job.status == "blocked"


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
            Job.__table__,
            JobEvent.__table__,
        ],
    )
    return create_session_factory(engine)()


def _patch_jobs_session_scope(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session,
) -> None:
    @contextmanager
    def override_session_scope() -> Iterator[object]:
        yield session

    monkeypatch.setattr("adaptive_rag.cli.jobs.session_scope", override_session_scope)
