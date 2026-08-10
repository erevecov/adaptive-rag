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
from adaptive_rag.db.models import Source, Workspace
from adaptive_rag.db.repositories import SourceRepository, WorkspaceRepository
from adaptive_rag.db.session import create_session_factory


def test_authoring_commands_are_registered() -> None:
    runner = CliRunner()

    workspaces = runner.invoke(app, ["workspaces", "--help"])
    sources = runner.invoke(app, ["sources", "--help"])

    assert workspaces.exit_code == 0
    assert "create" in workspaces.stdout
    assert "list" in workspaces.stdout
    assert "show" in workspaces.stdout
    assert sources.exit_code == 0
    assert "create" in sources.stdout
    assert "list" in sources.stdout
    assert "show" in sources.stdout


def test_workspaces_create_list_and_show_output_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    _patch_authoring_session_scope(monkeypatch, session=session)
    runner = CliRunner()

    created = runner.invoke(app, ["workspaces", "create", "--name", "Demo"])

    assert created.exit_code == 0
    workspace = json.loads(created.stdout)
    assert workspace["name"] == "Demo"
    assert workspace["embedding_mode"] == "dense_sparse"
    assert workspace["retrieval_contextualization_enabled"] is True
    assert workspace["budget_config_json"] is None

    listed = runner.invoke(app, ["workspaces", "list"])
    shown = runner.invoke(
        app,
        ["workspaces", "show", "--workspace-id", workspace["id"]],
    )

    assert listed.exit_code == 0
    assert [item["id"] for item in json.loads(listed.stdout)["items"]] == [
        workspace["id"]
    ]
    assert shown.exit_code == 0
    assert json.loads(shown.stdout)["id"] == workspace["id"]


def test_workspaces_show_missing_workspace_exits_with_stable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    _patch_authoring_session_scope(monkeypatch, session=session)

    result = CliRunner().invoke(
        app,
        ["workspaces", "show", "--workspace-id", str(uuid4())],
    )

    assert result.exit_code == 1
    assert result.stderr.strip() == "workspace not found"


def test_sources_create_list_and_show_output_json_without_ingestion_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="Demo")
    session.commit()
    _patch_authoring_session_scope(monkeypatch, session=session)
    runner = CliRunner()

    markdown = runner.invoke(
        app,
        [
            "sources",
            "create",
            "--workspace-id",
            str(workspace.id),
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
            "--workspace-id",
            str(workspace.id),
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
    assert markdown_payload["workspace_id"] == str(workspace.id)
    assert markdown_payload["source_type"] == "markdown"
    assert markdown_payload["external_id"] == "notes.md"
    assert markdown_payload["tags"] == ["docs", "local"]
    assert markdown_payload["extra_metadata"] == {"content": "# Notes"}
    assert url_payload["source_type"] == "url"
    assert url_payload["extra_metadata"] is None

    listed = runner.invoke(
        app, ["sources", "list", "--workspace-id", str(workspace.id)]
    )
    shown = runner.invoke(
        app,
        [
            "sources",
            "show",
            "--workspace-id",
            str(workspace.id),
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
    workspace = WorkspaceRepository(session).create(name="Demo")
    SourceRepository(session).create(
        workspace_id=workspace.id,
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
            "--workspace-id",
            str(workspace.id),
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
            "--workspace-id",
            str(workspace.id),
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


def test_sources_show_missing_workspace_and_source_exit_with_stable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="Demo")
    session.commit()
    _patch_authoring_session_scope(monkeypatch, session=session)
    runner = CliRunner()

    missing_workspace = runner.invoke(
        app,
        [
            "sources",
            "list",
            "--workspace-id",
            str(uuid4()),
        ],
    )
    missing_source = runner.invoke(
        app,
        [
            "sources",
            "show",
            "--workspace-id",
            str(workspace.id),
            "--source-id",
            str(uuid4()),
        ],
    )

    assert missing_workspace.exit_code == 1
    assert missing_workspace.stderr.strip() == "workspace not found"
    assert missing_source.exit_code == 1
    assert missing_source.stderr.strip() == "source not found"


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Workspace.__table__, Source.__table__])
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
        "adaptive_rag.cli.workspaces.session_scope",
        override_session_scope,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.sources.session_scope",
        override_session_scope,
    )
