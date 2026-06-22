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
    assert "run-worker" in result.stdout


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
