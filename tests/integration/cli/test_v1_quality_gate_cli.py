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
    Job,
    JobEvent,
    Project,
    Source,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def test_v1_quality_gate_command_is_registered() -> None:
    runner = CliRunner()

    root = runner.invoke(app, ["--help"])
    v1 = runner.invoke(app, ["v1", "--help"])

    assert root.exit_code == 0
    assert "v1" in root.stdout
    assert v1.exit_code == 0
    assert "quality-gate" in v1.stdout


def test_v1_quality_gate_emits_release_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    _patch_v1_session_scope(monkeypatch, session=session)

    result = CliRunner().invoke(
        app,
        [
            "v1",
            "quality-gate",
            "--project-name",
            "V1 Release Demo",
            "--source-external-id",
            "release-demo.md",
            "--worker-id",
            "v1-quality-gate-test",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "succeeded"
    assert payload["release_decision"] == "ready_for_v1_0"
    assert payload["first_run"]["status"] == "succeeded"
    assert payload["first_run"]["project"]["name"] == "V1 Release Demo"
    assert payload["first_run"]["source"]["external_id"] == "release-demo.md"
    assert payload["first_run"]["job"]["status"] == "succeeded"
    assert payload["first_run"]["chunk_count"] >= 1
    assert payload["first_run"]["citation_count"] >= 1
    assert all(criterion["status"] == "passed" for criterion in payload["criteria"])
    assert {
        criterion["id"] for criterion in payload["criteria"]
    } == {
        "public_product_flow",
        "ingestion_job_state",
        "indexed_evidence",
        "cited_chat",
        "public_follow_up_commands",
        "opt_in_boundaries",
    }
    assert "hosted_qwen" in payload["deferred_defaults"]
    assert "manual git tag or GitHub release" in payload["manual_release_notes"]


def test_v1_quality_gate_writes_output_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    session = _make_session()
    _patch_v1_session_scope(monkeypatch, session=session)
    output_path = tmp_path / "v1-quality-gate.json"

    result = CliRunner().invoke(
        app,
        [
            "v1",
            "quality-gate",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert result.stdout == ""
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "succeeded"
    assert payload["release_decision"] == "ready_for_v1_0"


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


def _patch_v1_session_scope(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session,
) -> None:
    @contextmanager
    def override_session_scope() -> Iterator[object]:
        yield session

    monkeypatch.setattr(
        "adaptive_rag.cli.v1.session_scope",
        override_session_scope,
    )
