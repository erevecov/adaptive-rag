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
from adaptive_rag.config.settings import Settings
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Project
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.evals.models import EvalRunReport
from adaptive_rag.evals.strategy_gate_runner import (
    StrategyGateReport,
    StrategyGateRow,
)
from adaptive_rag.provider_usage import ProviderCallRecord, ProviderTokenUsage


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
    dense_provider = object()
    sparse_provider = object()

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
            default_strategy="dense_sparse",
            recommended_default="dense_sparse",
            dense_baseline=baseline,
            rows=(
                StrategyGateRow(
                    strategy="dense",
                    status="passed",
                    decision="promote",
                    reason=(
                        "dense baseline passes as the stable comparison baseline"
                    ),
                    metrics={"retrieval_hit_rate": 1.0},
                    comparison_metrics={},
                ),
            ),
        )

    monkeypatch.setattr(
        "adaptive_rag.cli.evals.get_cli_dense_embedding_provider",
        lambda *, usage_tracker: dense_provider,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.evals.get_cli_sparse_embedding_provider",
        lambda *, usage_tracker: sparse_provider,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.evals.run_retrieval_strategy_gate_eval_suite",
        fake_strategy_gate,
    )

    result = CliRunner().invoke(app, ["evals", "strategy-gate", str(suite_path)])

    assert result.exit_code == 0
    assert captured["session"] is session
    assert captured["suite_id"] == "cli-strategy-gate"
    assert captured["provider"] is dense_provider
    assert captured["sparse_provider"] is sparse_provider
    assert json.loads(result.stdout) == {
        "suite_id": "cli-strategy-gate",
        "status": "passed",
        "default_strategy": "dense_sparse",
        "recommended_default": "dense_sparse",
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
                "reason": "dense baseline passes as the stable comparison baseline",
                "metrics": {"retrieval_hit_rate": 1.0},
                "comparison_metrics": {},
            }
        ],
    }


def test_evals_strategy_gate_command_outputs_provider_usage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = _make_session()
    _patch_session_scope(monkeypatch, session=session)
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "cli-strategy-gate-usage",
            "thresholds": {"retrieval_hit_rate": 1.0},
            "evidence": [],
            "retrieval_cases": [],
            "chat_cases": [],
        },
    )
    captured: dict[str, object] = {}

    def fake_dense_provider(*, usage_tracker):
        captured["dense_tracker"] = usage_tracker
        usage_tracker.record(
            ProviderCallRecord(
                provider="qwen",
                model="text-embedding-v4",
                operation="embedding",
                outcome="succeeded",
                duration_ms=17,
                usage=ProviderTokenUsage(input_tokens=11, total_tokens=11),
                usage_source="provider_reported",
                estimated_cost_usd=0.000011,
                request_id="secret-request-id",
            )
        )
        return object()

    def fake_sparse_provider(*, usage_tracker):
        captured["sparse_tracker"] = usage_tracker
        usage_tracker.record(
            ProviderCallRecord(
                provider="qwen",
                model="qwen-sparse-embedding",
                operation="embedding",
                outcome="succeeded",
                duration_ms=23,
                usage=ProviderTokenUsage(input_tokens=13, total_tokens=13),
                usage_source="provider_reported",
                estimated_cost_usd=0.000013,
            )
        )
        return object()

    def fake_strategy_gate(
        session_arg: Session,
        suite,
        *,
        provider=None,
        sparse_provider=None,
    ) -> StrategyGateReport:
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
            default_strategy="dense_sparse",
            recommended_default="dense_sparse",
            dense_baseline=baseline,
            rows=(
                StrategyGateRow(
                    strategy="dense",
                    status="passed",
                    decision="promote",
                    reason=(
                        "dense baseline passes as the stable comparison baseline"
                    ),
                    metrics={"retrieval_hit_rate": 1.0},
                    comparison_metrics={},
                ),
            ),
        )

    monkeypatch.setattr(
        "adaptive_rag.cli.evals.get_cli_dense_embedding_provider",
        fake_dense_provider,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.evals.get_cli_sparse_embedding_provider",
        fake_sparse_provider,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.evals.run_retrieval_strategy_gate_eval_suite",
        fake_strategy_gate,
    )

    result = CliRunner().invoke(app, ["evals", "strategy-gate", str(suite_path)])

    assert result.exit_code == 0
    assert captured["dense_tracker"] is captured["sparse_tracker"]
    payload = json.loads(result.stdout)
    assert payload["provider_usage"] == {
        "total_call_count": 2,
        "total_estimated_cost_usd": 0.000024,
        "operations": [
            {
                "operation": "embedding",
                "provider": "qwen",
                "model": "qwen-sparse-embedding",
                "call_count": 1,
                "succeeded_count": 1,
                "failed_count": 0,
                "blocked_count": 0,
                "input_tokens": 13,
                "output_tokens": None,
                "total_tokens": 13,
                "input_count": None,
                "estimated_cost_usd": 0.000013,
                "usage_unavailable_count": 0,
            },
            {
                "operation": "embedding",
                "provider": "qwen",
                "model": "text-embedding-v4",
                "call_count": 1,
                "succeeded_count": 1,
                "failed_count": 0,
                "blocked_count": 0,
                "input_tokens": 11,
                "output_tokens": None,
                "total_tokens": 11,
                "input_count": None,
                "estimated_cost_usd": 0.000011,
                "usage_unavailable_count": 0,
            },
        ],
    }
    assert "secret-request-id" not in result.stdout


def test_evals_strategy_gate_can_require_live_qwen_sparse_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "adaptive_rag.cli.evals.get_settings",
        lambda: Settings(_env_file=None),
    )
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "cli-strategy-gate-live-required",
            "thresholds": {"retrieval_hit_rate": 1.0},
            "evidence": [],
            "retrieval_cases": [],
            "chat_cases": [],
        },
    )

    result = CliRunner().invoke(
        app,
        [
            "evals",
            "strategy-gate",
            str(suite_path),
            "--require-live-qwen-sparse",
        ],
    )

    assert result.exit_code == 1
    assert (
        "live Qwen sparse strategy gate requires "
        "ADAPTIVE_RAG_PROVIDER_RUNTIME_MODE=live"
    ) in result.stderr
    assert "ADAPTIVE_RAG_SPARSE_EMBEDDING_PROVIDER=qwen" in result.stderr
    assert "ADAPTIVE_RAG_QWEN_API_KEY" in result.stderr
    assert "ADAPTIVE_RAG_PROVIDER_MAX_COST_USD" in result.stderr


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
