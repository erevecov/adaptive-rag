from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from typer.testing import CliRunner

from adaptive_rag.cli.app import app
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Chunk,
    Document,
    DocumentVersion,
    GlobalChatModel,
    Job,
    JobEvent,
    Project,
    ProjectChatModel,
    ProjectRuntimeSlotOverride,
    ProviderConnection,
    ProviderModelCatalog,
    RuntimeSlotDefault,
    Source,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def test_acceptance_command_is_registered() -> None:
    runner = CliRunner()

    root = runner.invoke(app, ["--help"])
    acceptance = runner.invoke(app, ["acceptance", "--help"])

    assert root.exit_code == 0
    assert "acceptance" in root.stdout
    assert acceptance.exit_code == 0
    assert "runtime-settings-smoke" in acceptance.stdout


def test_runtime_settings_acceptance_smoke_uses_persisted_effective_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    _patch_acceptance_session_scope(monkeypatch, session=session)

    result = CliRunner().invoke(
        app,
        [
            "acceptance",
            "runtime-settings-smoke",
            "--project-name",
            "Runtime Acceptance Demo",
            "--source-external-id",
            "runtime-acceptance.md",
            "--worker-id",
            "runtime-acceptance-test",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "succeeded"
    assert payload["first_run"]["status"] == "succeeded"
    assert payload["first_run"]["project"]["name"] == "Runtime Acceptance Demo"
    assert payload["first_run"]["source"]["external_id"] == "runtime-acceptance.md"
    assert payload["first_run"]["citation_count"] >= 1
    assert all(criterion["status"] == "passed" for criterion in payload["criteria"])
    assert {
        criterion["id"] for criterion in payload["criteria"]
    } == {
        "model_catalog_synced",
        "global_runtime_defaults",
        "project_runtime_override",
        "effective_runtime_resolution",
        "cited_chat",
        "secret_values_not_exposed",
    }

    runtime = payload["runtime_settings"]
    assert runtime["global_connection"]["provider"] == "fake"
    assert runtime["global_connection"]["connection_type"] == "fake"
    assert runtime["model_catalog"]["synced_count"] >= 3
    assert "retrieval-grounded-local-v1" in runtime["model_catalog"]["model_ids"]
    assert "fake-embedding-v1" in runtime["model_catalog"]["model_ids"]
    assert runtime["global_slots"]["chat"]["model_id"] == "retrieval-grounded-local-v1"
    assert runtime["global_slots"]["dense_embedding"]["model_id"] == "fake-embedding-v1"
    assert runtime["effective_project_settings"]["chat"]["source"] == "inherited"
    assert (
        runtime["effective_project_settings"]["dense_embedding"]["source"]
        == "overridden"
    )
    assert runtime["resolved_runtime"]["chat"]["provider"] == "fake"
    assert runtime["resolved_runtime"]["chat"]["model_id"] == (
        "retrieval-grounded-local-v1"
    )
    assert runtime["resolved_runtime"]["dense_embedding"]["provider"] == "fake"
    assert runtime["resolved_runtime"]["dense_embedding"]["model_id"] == (
        "fake-embedding-v1"
    )
    assert "hosted_qwen" in payload["opt_in_systems"]
    assert "sk-runtime-acceptance-secret" not in result.stdout


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
            ProviderConnection.__table__,
            ProviderModelCatalog.__table__,
            RuntimeSlotDefault.__table__,
            GlobalChatModel.__table__,
            ProjectRuntimeSlotOverride.__table__,
            ProjectChatModel.__table__,
        ],
    )
    return create_session_factory(engine)()


def _patch_acceptance_session_scope(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session,
) -> None:
    @contextmanager
    def override_session_scope() -> Iterator[object]:
        yield session

    monkeypatch.setattr(
        "adaptive_rag.cli.acceptance.session_scope",
        override_session_scope,
    )
