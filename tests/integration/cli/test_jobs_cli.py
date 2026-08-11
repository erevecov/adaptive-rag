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
    JobAttempt,
    JobEvent,
    JobQueue,
    Source,
    Workspace,
)
from adaptive_rag.db.repositories import (
    JobRepository,
    SourceRepository,
    WorkspaceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.jobs.handlers import build_ingestion_registry


def test_job_platform_commands_are_registered() -> None:
    result = CliRunner().invoke(app, ["jobs", "--help"])

    assert result.exit_code == 0
    assert "enqueue-ingest-source" in result.stdout
    assert "enqueue" in result.stdout
    assert "list" in result.stdout
    assert "show" in result.stdout
    assert "cancel" in result.stdout
    assert "retry" in result.stdout
    assert "unblock" in result.stdout
    assert "worker" in result.stdout
    assert "scheduler" in result.stdout
    assert "schedules" in result.stdout
    assert "queues" in result.stdout
    assert "workers" in result.stdout
    assert "run-worker" in result.stdout


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["jobs", "worker", "--help"], "--once"),
        (["jobs", "schedules", "list", "--help"], "--workspace-id"),
        (["jobs", "queues", "list", "--help"], "Usage:"),
        (["jobs", "workers", "list", "--help"], "Usage:"),
    ],
)
def test_job_platform_nested_command_help(
    args: list[str], expected: str
) -> None:
    result = CliRunner().invoke(app, args)

    assert result.exit_code == 0
    assert expected in result.stdout


def test_jobs_enqueue_rejects_invalid_json_before_opening_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened = False

    def forbidden_runtime():
        nonlocal opened
        opened = True
        raise AssertionError("database runtime must not be created")

    monkeypatch.setattr("adaptive_rag.cli.jobs._job_runtime", forbidden_runtime)

    result = CliRunner().invoke(
        app,
        [
            "jobs",
            "enqueue",
            "--job-type",
            "ingest_source",
            "--workspace-id",
            "00000000-0000-0000-0000-000000000001",
            "--payload-json",
            "[1, 2]",
        ],
    )

    assert result.exit_code == 2
    assert "must be a JSON object" in result.stderr
    assert opened is False


def test_jobs_enqueue_list_and_show_ingestion_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        workspace_id=workspace.id,
        source_type="markdown",
        external_id="demo.md",
        extra_metadata={"content": "# Demo"},
    )
    session.commit()
    _patch_jobs_session_scope(monkeypatch, session=session)
    _patch_job_runtime(monkeypatch, session=session)
    runner = CliRunner()

    created = runner.invoke(
        app,
        [
            "jobs",
            "enqueue-ingest-source",
            "--workspace-id",
            str(workspace.id),
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
            "--workspace-id",
            str(workspace.id),
        ],
    )
    shown = runner.invoke(
        app,
        [
            "jobs",
            "show",
            "--workspace-id",
            str(workspace.id),
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


def test_jobs_unblock_requeues_blocked_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    job = JobRepository(session).create(
        workspace_id=workspace.id, job_type="ingest_source"
    )
    JobRepository(session).block(
        workspace_id=workspace.id, job_id=job.id, reason="blocked"
    )
    session.commit()
    _patch_job_runtime(monkeypatch, session=session)

    result = CliRunner().invoke(
        app,
        [
            "jobs",
            "unblock",
            "--workspace-id",
            str(workspace.id),
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
    workspace = WorkspaceRepository(session).create(name="demo")
    session.commit()
    _patch_jobs_session_scope(monkeypatch, session=session)
    _patch_job_runtime(monkeypatch, session=session)
    runner = CliRunner()

    missing_source = runner.invoke(
        app,
        [
            "jobs",
            "enqueue-ingest-source",
            "--workspace-id",
            str(workspace.id),
            "--source-id",
            str(workspace.id),
        ],
    )
    missing_job = runner.invoke(
        app,
        [
            "jobs",
            "show",
            "--workspace-id",
            str(workspace.id),
            "--job-id",
            str(workspace.id),
        ],
    )

    assert missing_source.exit_code == 1
    assert missing_source.stderr.strip() == "source not found"
    assert missing_job.exit_code == 1
    assert missing_job.stderr.startswith("Job not found:")


def test_jobs_run_worker_once_processes_ingest_source_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        workspace_id=workspace.id,
        source_type="markdown",
        external_id="demo.md",
        extra_metadata={"content": "# Demo\n\nEvidence"},
    )
    job = JobRepository(session).create(
        workspace_id=workspace.id,
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
            "--workspace-id",
            str(workspace.id),
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

    stored_job = JobRepository(session).get(workspace_id=workspace.id, job_id=job.id)
    document_version = session.scalars(select(DocumentVersion)).one()
    assert stored_job is not None
    assert stored_job.status == "succeeded"
    assert document_version.normalized_text == "# Demo\n\nEvidence"


def test_jobs_run_worker_once_reports_blocked_ingestion_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        workspace_id=workspace.id,
        source_type="markdown",
        external_id="missing.md",
    )
    job = JobRepository(session).create(
        workspace_id=workspace.id,
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
            "--workspace-id",
            str(workspace.id),
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

    stored_job = JobRepository(session).get(workspace_id=workspace.id, job_id=job.id)
    assert stored_job is not None
    assert stored_job.status == "blocked"


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Workspace.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
            JobQueue.__table__,
            Job.__table__,
            JobAttempt.__table__,
            JobEvent.__table__,
        ],
    )
    session = create_session_factory(engine)()
    session.add_all(
        [JobQueue(name="default"), JobQueue(name="ingestion"), JobQueue(name="system")]
    )
    session.commit()
    return session


def _patch_jobs_session_scope(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session,
) -> None:
    @contextmanager
    def override_session_scope() -> Iterator[object]:
        yield session

    monkeypatch.setattr("adaptive_rag.cli.jobs.session_scope", override_session_scope)


def _patch_job_runtime(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session,
) -> None:
    def factory():
        return session

    registry = build_ingestion_registry(session_factory=factory)  # type: ignore[arg-type]
    monkeypatch.setattr(
        "adaptive_rag.cli.jobs._job_runtime", lambda: (factory, registry)
    )
