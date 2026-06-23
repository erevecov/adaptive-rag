"""CLI coverage for the M31 retrieval strategy gate command."""

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
from adaptive_rag.db.models import Project
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.evals.models import EvalRunReport
from adaptive_rag.evals.strategy_gate_runner import (
    StrategyGateReport,
    StrategyGateRow,
)


def test_evals_strategy_gate_command_outputs_decision_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = _make_session()
    _patch_session_scope(monkeypatch, session=session)
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "cli-strategy-gate",
            "thresholds": {"retrieval_hit_rate": 1.0},
            "evidence": [],
            "retrieval_cases": [],
            "chat_cases": [],
        },
    )
    captured: dict[str, object] = {}

    def fake_strategy_gate(
        session_arg: Session,
        suite,
        *,
        provider=None,
        sparse_provider=None,
    ) -> StrategyGateReport:
        captured["session"] = session_arg
        captured["suite_id"] = suite.suite_id
        captured["provider"] = provider
        captured["sparse_provider"] = sparse_provider
        baseline = EvalRunReport(
            suite_id=suite.suite_id,
            status="passed",
            metrics={"retrieval_hit_rate": 1.0},
            thresholds={"retrieval_hit_rate": 1.0},
            cases=(),
        )
        return StrategyGateReport(
            suite_id=suite.suite_id,
            status="passed",
            default_strategy="dense",
            recommended_default="dense",
            dense_baseline=baseline,
            rows=(
                StrategyGateRow(
                    strategy="dense",
                    status="passed",
                    decision="promote",
                    reason=(
                        "dense baseline passes and remains the recommended default"
                    ),
                    metrics={"retrieval_hit_rate": 1.0},
                    comparison_metrics={},
                ),
            ),
        )

    monkeypatch.setattr(
        "adaptive_rag.cli.evals.run_retrieval_strategy_gate_eval_suite",
        fake_strategy_gate,
    )

    result = CliRunner().invoke(app, ["evals", "strategy-gate", str(suite_path)])

    assert result.exit_code == 0
    assert captured["session"] is session
    assert captured["suite_id"] == "cli-strategy-gate"
    assert captured["provider"] is not None
    assert captured["sparse_provider"] is not None
    assert json.loads(result.stdout) == {
        "suite_id": "cli-strategy-gate",
        "status": "passed",
        "default_strategy": "dense",
        "recommended_default": "dense",
        "dense_baseline": {
            "suite_id": "cli-strategy-gate",
            "status": "passed",
            "metrics": {"retrieval_hit_rate": 1.0},
            "thresholds": {"retrieval_hit_rate": 1.0},
            "cases": [],
        },
        "strategy_decisions": [
            {
                "strategy": "dense",
                "status": "passed",
                "decision": "promote",
                "reason": "dense baseline passes and remains the recommended default",
                "metrics": {"retrieval_hit_rate": 1.0},
                "comparison_metrics": {},
            }
        ],
    }


def _patch_session_scope(
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
    Base.metadata.create_all(engine, tables=[Project.__table__])
    return create_session_factory(engine)()


def _write_suite(tmp_path: Path, payload: object) -> Path:
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(json.dumps(payload), encoding="utf-8")
    return suite_path
