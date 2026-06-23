from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from typer.testing import CliRunner

from adaptive_rag.cli.app import app
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Project, Source
from adaptive_rag.db.repositories import ProjectRepository, SourceRepository
from adaptive_rag.db.session import create_session_factory


def test_authoring_commands_are_registered() -> None:
    runner = CliRunner()

    projects = runner.invoke(app, ["projects", "--help"])
    sources = runner.invoke(app, ["sources", "--help"])

    assert projects.exit_code == 0
    assert "create" in projects.stdout
    assert "list" in projects.stdout
    assert "show" in projects.stdout
    assert sources.exit_code == 0
    assert "create" in sources.stdout
    assert "list" in sources.stdout
    assert "show" in sources.stdout


def test_projects_create_list_and_show_output_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    _patch_authoring_session_scope(monkeypatch, session=session)
    runner = CliRunner()

    created = runner.invoke(app, ["projects", "create", "--name", "Demo"])

    assert created.exit_code == 0
    project = json.loads(created.stdout)
    assert project["name"] == "Demo"
    assert project["embedding_mode"] == "dense"
    assert project["retrieval_contextualization_enabled"] is True
    assert project["budget_config_json"] is None

    listed = runner.invoke(app, ["projects", "list"])
    shown = runner.invoke(
        app,
        ["projects", "show", "--project-id", project["id"]],
    )

    assert listed.exit_code == 0
    assert [item["id"] for item in json.loads(listed.stdout)["items"]] == [
        project["id"]
    ]
    assert shown.exit_code == 0
    assert json.loads(shown.stdout)["id"] == project["id"]


def test_projects_show_missing_project_exits_with_stable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    _patch_authoring_session_scope(monkeypatch, session=session)

    result = CliRunner().invoke(
        app,
        ["projects", "show", "--project-id", str(uuid4())],
    )

    assert result.exit_code == 1
    assert result.stderr.strip() == "project not found"


def test_sources_create_list_and_show_output_json_without_ingestion_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="Demo")
    session.commit()
    _patch_authoring_session_scope(monkeypatch, session=session)
    runner = CliRunner()

    markdown = runner.invoke(
        app,
        [
            "sources",
            "create",
            "--project-id",
            str(project.id),
            "--source-type",
            "markdown",
            "--external-id",
            "notes.md",
            "--content",
            "# Notes",
            "--tag",
            "docs",
            "--tag",
            "local",
        ],
    )
    url = runner.invoke(
        app,
        [
            "sources",
            "create",
            "--project-id",
            str(project.id),
            "--source-type",
            "url",
            "--external-id",
            "https://example.com/doc",
        ],
    )

    assert markdown.exit_code == 0
    assert url.exit_code == 0
    markdown_payload = json.loads(markdown.stdout)
    url_payload = json.loads(url.stdout)
    assert markdown_payload["project_id"] == str(project.id)
    assert markdown_payload["source_type"] == "markdown"
    assert markdown_payload["external_id"] == "notes.md"
    assert markdown_payload["tags"] == ["docs", "local"]
    assert markdown_payload["extra_metadata"] == {"content": "# Notes"}
    assert url_payload["source_type"] == "url"
    assert url_payload["extra_metadata"] is None

    listed = runner.invoke(app, ["sources", "list", "--project-id", str(project.id)])
    shown = runner.invoke(
        app,
        [
            "sources",
            "show",
            "--project-id",
            str(project.id),
            "--source-id",
            markdown_payload["id"],
        ],
    )

    assert listed.exit_code == 0
    assert {item["id"] for item in json.loads(listed.stdout)["items"]} == {
        markdown_payload["id"],
        url_payload["id"],
    }
    assert shown.exit_code == 0
    assert json.loads(shown.stdout)["id"] == markdown_payload["id"]


def test_sources_create_rejects_missing_text_content_and_duplicate_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="Demo")
    SourceRepository(session).create(
        project_id=project.id,
        source_type="url",
        external_id="https://example.com/doc",
    )
    session.commit()
    _patch_authoring_session_scope(monkeypatch, session=session)
    runner = CliRunner()

    missing_content = runner.invoke(
        app,
        [
            "sources",
            "create",
            "--project-id",
            str(project.id),
            "--source-type",
            "markdown",
            "--external-id",
            "notes.md",
        ],
    )
    duplicate = runner.invoke(
        app,
        [
            "sources",
            "create",
            "--project-id",
            str(project.id),
            "--source-type",
            "url",
            "--external-id",
            "https://example.com/doc",
        ],
    )

    assert missing_content.exit_code == 1
    assert missing_content.stderr.strip() == (
        "markdown source requires extra_metadata.content"
    )
    assert duplicate.exit_code == 1
    assert duplicate.stderr.strip() == "source already exists"


def test_sources_show_missing_project_and_source_exit_with_stable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="Demo")
    session.commit()
    _patch_authoring_session_scope(monkeypatch, session=session)
    runner = CliRunner()

    missing_project = runner.invoke(
        app,
        [
            "sources",
            "list",
            "--project-id",
            str(uuid4()),
        ],
    )
    missing_source = runner.invoke(
        app,
        [
            "sources",
            "show",
            "--project-id",
            str(project.id),
            "--source-id",
            str(uuid4()),
        ],
    )

    assert missing_project.exit_code == 1
    assert missing_project.stderr.strip() == "project not found"
    assert missing_source.exit_code == 1
    assert missing_source.stderr.strip() == "source not found"


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Project.__table__, Source.__table__])
    return create_session_factory(engine)()


def _patch_authoring_session_scope(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session: Session,
) -> None:
    @contextmanager
    def override_session_scope() -> Iterator[Session]:
        yield session

    monkeypatch.setattr(
        "adaptive_rag.cli.projects.session_scope",
        override_session_scope,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.sources.session_scope",
        override_session_scope,
    )
