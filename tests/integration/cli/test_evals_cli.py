"""Tests del comando CLI de evals."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from adaptive_rag.cli.app import app
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Chunk,
    Document,
    DocumentVersion,
    Project,
    Source,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def test_evals_run_command_outputs_json_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = _make_session()
    _patch_evals_dependencies(monkeypatch, session=session)
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "cli-empty",
            "thresholds": {},
            "evidence": [],
            "retrieval_cases": [],
            "chat_cases": [],
        },
    )

    result = CliRunner().invoke(app, ["evals", "run", str(suite_path)])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "suite_id": "cli-empty",
        "status": "passed",
        "metrics": {
            "chat_case_count": 0.0,
            "chat_citation_coverage": 1.0,
            "chat_passed_count": 0.0,
            "retrieval_case_count": 0.0,
            "retrieval_hit_rate": 1.0,
            "retrieval_passed_count": 0.0,
        },
        "thresholds": {},
        "cases": [],
    }


def test_evals_run_command_writes_output_and_exits_one_on_failed_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = _make_session()
    _patch_evals_dependencies(monkeypatch, session=session)
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "cli-fail",
            "thresholds": {"retrieval_hit_rate": 1.0},
            "evidence": [
                {
                    "id": "alpha",
                    "text": "Alpha original evidence",
                    "source_type": "markdown",
                    "source_external_id": "alpha.md",
                },
                {
                    "id": "far",
                    "text": "Far unrelated evidence",
                    "source_type": "markdown",
                    "source_external_id": "far.md",
                },
            ],
            "retrieval_cases": [
                {
                    "id": "retrieve-wrong",
                    "query": "Far unrelated evidence",
                    "limit": 1,
                    "expected_evidence_ids": ["alpha"],
                }
            ],
            "chat_cases": [],
        },
    )
    output_path = tmp_path / "report.json"

    result = CliRunner().invoke(
        app,
        ["evals", "run", str(suite_path), "--output", str(output_path)],
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["suite_id"] == "cli-fail"
    assert data["status"] == "failed"
    assert data["metrics"]["retrieval_hit_rate"] == 0.0
    assert data["cases"][0]["errors"] == ["missing expected evidence: alpha"]


def test_evals_run_command_reports_missing_suite(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.json"

    result = CliRunner().invoke(app, ["evals", "run", str(missing_path)])

    assert result.exit_code == 1
    assert "could not read eval suite" in result.output


def _patch_evals_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session: Session,
) -> None:
    @contextmanager
    def override_session_scope() -> Iterator[Session]:
        yield session

    monkeypatch.setattr(
        "adaptive_rag.cli.evals.session_scope",
        override_session_scope,
    )


def _make_session() -> Session:
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
        ],
    )
    return create_session_factory(engine)()


def _write_suite(tmp_path: Path, payload: object) -> Path:
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(json.dumps(payload), encoding="utf-8")
    return suite_path
