"""Tests del comando CLI de evals."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from adaptive_rag.chat import ChatRunnerOutput, ChatRunnerRequest
from adaptive_rag.chat.tools import ChatTools
from adaptive_rag.cli.app import app
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    EMBEDDING_DIMENSIONS,
    Chunk,
    Document,
    DocumentVersion,
    GraphProjection,
    Project,
    Source,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.evals import EvalRunOptions
from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderCallRecord,
    ProviderTokenUsage,
)
from adaptive_rag.rerank import RerankRequest, RerankResult, RerankScore


class UsageRecordingEmbeddingProvider:
    provider_name = "qwen"
    model_name = "text-embedding-v4"
    dimensions = EMBEDDING_DIMENSIONS

    def __init__(
        self,
        mapping: dict[str, list[float]],
        *,
        tracker: InMemoryProviderUsageTracker,
    ) -> None:
        self._mapping = mapping
        self._tracker = tracker
        self.inputs: list[str] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.inputs.extend(texts)
        token_count = sum(len(text.split()) for text in texts)
        self._tracker.record(
            ProviderCallRecord(
                provider=self.provider_name,
                model=self.model_name,
                operation="embedding",
                outcome="succeeded",
                duration_ms=3,
                usage=ProviderTokenUsage(
                    input_tokens=token_count,
                    total_tokens=token_count,
                    input_count=len(texts),
                ),
                usage_source="provider_reported",
                estimated_cost_usd=0.0001 * len(texts),
            )
        )
        return [list(self._mapping[text]) for text in texts]


class UsageRecordingChatRunner:
    provider_name = "qwen"
    model_name = "qwen-plus"

    def __init__(self, *, tracker: InMemoryProviderUsageTracker) -> None:
        self._tracker = tracker
        self.requests: list[ChatRunnerRequest] = []

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        self.requests.append(request)
        retrieval = tools.retrieval.search(
            query=request.message,
            limit=request.retrieval_limit,
            metadata_filter=request.metadata_filter,
        )
        self._tracker.record(
            ProviderCallRecord(
                provider=self.provider_name,
                model=self.model_name,
                operation="chat",
                outcome="succeeded",
                duration_ms=20,
                usage=ProviderTokenUsage(
                    input_tokens=40,
                    output_tokens=10,
                    total_tokens=50,
                ),
                usage_source="provider_reported",
                estimated_cost_usd=0.0005,
            )
        )
        return ChatRunnerOutput(
            answer="Alpha answer",
            cited_chunk_ids=tuple(
                UUID(result["chunk_id"]) for result in retrieval.results
            ),
        )


class UsageRecordingRerankProvider:
    provider_name = "qwen"
    model_name = "qwen3-rerank"

    def __init__(self, *, tracker: InMemoryProviderUsageTracker) -> None:
        self._tracker = tracker
        self.requests: list[RerankRequest] = []

    def rerank(self, request: RerankRequest) -> RerankResult:
        self.requests.append(request)
        token_count = len(request.query.split()) + sum(
            len(candidate.text.split()) for candidate in request.candidates
        )
        self._tracker.record(
            ProviderCallRecord(
                provider=self.provider_name,
                model=self.model_name,
                operation="rerank",
                outcome="succeeded",
                duration_ms=8,
                usage=ProviderTokenUsage(
                    input_tokens=token_count,
                    total_tokens=token_count,
                    input_count=len(request.candidates),
                ),
                usage_source="provider_reported",
                estimated_cost_usd=0.0002,
            )
        )
        scored = sorted(
            enumerate(request.candidates, start=1),
            key=lambda item: (
                0 if item[1].text == "Alpha original evidence" else 1,
                item[0],
            ),
        )
        return RerankResult(
            provider_name=self.provider_name,
            model_name=self.model_name,
            scores=tuple(
                RerankScore(
                    candidate_id=candidate.candidate_id,
                    score=1.0 if candidate.text == "Alpha original evidence" else 0.1,
                    original_rank=original_rank,
                    rerank_rank=rerank_rank,
                )
                for rerank_rank, (original_rank, candidate) in enumerate(
                    scored[: request.top_k],
                    start=1,
                )
            ),
        )


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


def test_evals_run_command_hosted_mode_outputs_provider_usage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = _make_session()
    _patch_evals_dependencies(monkeypatch, session=session)
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "cli-hosted",
            "thresholds": {
                "retrieval_hit_rate": 1.0,
                "chat_citation_coverage": 1.0,
            },
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
                    "id": "retrieve-alpha",
                    "query": "Alpha original evidence",
                    "limit": 2,
                    "expected_evidence_ids": ["alpha"],
                }
            ],
            "chat_cases": [
                {
                    "id": "chat-alpha",
                    "message": "Alpha original evidence",
                    "retrieval_limit": 2,
                    "expected_evidence_ids": ["alpha"],
                    "expected_tool_queries": ["Alpha original evidence"],
                }
            ],
        },
    )
    tracker = InMemoryProviderUsageTracker()
    provider = UsageRecordingEmbeddingProvider(
        {
            "Alpha original evidence": _vector(0.0),
            "Far unrelated evidence": _vector(0.9),
        },
        tracker=tracker,
    )
    runner = UsageRecordingChatRunner(tracker=tracker)
    captured: dict[str, object] = {}

    def hosted_runtime(
        *,
        provider_name: str,
        max_cost_usd: float | None,
        include_reranker: bool = False,
    ) -> SimpleNamespace:
        captured["provider_name"] = provider_name
        captured["max_cost_usd"] = max_cost_usd
        captured["include_reranker"] = include_reranker
        return SimpleNamespace(
            provider=provider,
            chat_runner=runner,
            reranker=None,
            usage_tracker=tracker,
            options=EvalRunOptions(
                mode="hosted",
                provider=provider_name,
                max_cost_usd=max_cost_usd,
            ),
        )

    monkeypatch.setattr(
        "adaptive_rag.cli.evals.get_cli_hosted_eval_runtime",
        hosted_runtime,
        raising=False,
    )

    result = CliRunner().invoke(
        app,
        [
            "evals",
            "run",
            str(suite_path),
            "--mode",
            "hosted",
            "--max-cost-usd",
            "0.05",
        ],
    )

    assert result.exit_code == 0
    assert captured == {
        "provider_name": "qwen",
        "max_cost_usd": 0.05,
        "include_reranker": False,
    }
    assert provider.inputs == [
        "Alpha original evidence",
        "Far unrelated evidence",
        "Alpha original evidence",
        "Alpha original evidence",
        "Far unrelated evidence",
        "Alpha original evidence",
    ]
    assert [request.message for request in runner.requests] == [
        "Alpha original evidence"
    ]
    data = json.loads(result.stdout)
    assert data["mode"] == "hosted"
    assert data["status"] == "passed"
    assert data["metrics"]["retrieval_hit_rate"] == 1.0
    assert data["metrics"]["chat_citation_coverage"] == 1.0
    assert data["provider_usage"]["total_call_count"] == 5
    assert data["provider_usage"]["total_estimated_cost_usd"] == 0.0011
    assert data["provider_usage"]["operations"] == [
        {
            "operation": "chat",
            "provider": "qwen",
            "model": "qwen-plus",
            "call_count": 1,
            "succeeded_count": 1,
            "failed_count": 0,
            "blocked_count": 0,
            "input_tokens": 40,
            "output_tokens": 10,
            "total_tokens": 50,
            "input_count": None,
            "estimated_cost_usd": 0.0005,
            "usage_unavailable_count": 0,
        },
        {
            "operation": "embedding",
            "provider": "qwen",
            "model": "text-embedding-v4",
            "call_count": 4,
            "succeeded_count": 4,
            "failed_count": 0,
            "blocked_count": 0,
            "input_tokens": 18,
            "output_tokens": None,
            "total_tokens": 18,
            "input_count": 6,
            "estimated_cost_usd": 0.0006,
            "usage_unavailable_count": 0,
        },
    ]


def test_evals_run_command_hosted_mode_compares_reranked_retrieval(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = _make_session()
    _patch_evals_dependencies(monkeypatch, session=session)
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "cli-hosted-rerank",
            "thresholds": {"retrieval_hit_rate": 1.0},
            "evidence": [
                {
                    "id": "alpha",
                    "text": "Alpha original evidence",
                    "source_type": "markdown",
                    "source_external_id": "alpha.md",
                },
                {
                    "id": "distractor",
                    "text": "Beta distractor evidence",
                    "source_type": "markdown",
                    "source_external_id": "beta.md",
                },
            ],
            "retrieval_cases": [
                {
                    "id": "retrieve-alpha",
                    "query": "Which text answers alpha?",
                    "limit": 1,
                    "expected_evidence_ids": ["alpha"],
                }
            ],
            "chat_cases": [],
        },
    )
    tracker = InMemoryProviderUsageTracker()
    provider = UsageRecordingEmbeddingProvider(
        {
            "Alpha original evidence": _vector(0.2),
            "Beta distractor evidence": _vector(0.1),
            "Which text answers alpha?": _vector(0.0),
        },
        tracker=tracker,
    )
    runner = UsageRecordingChatRunner(tracker=tracker)
    reranker = UsageRecordingRerankProvider(tracker=tracker)
    captured: dict[str, object] = {}

    def hosted_runtime(
        *,
        provider_name: str,
        max_cost_usd: float | None,
        include_reranker: bool = False,
    ) -> SimpleNamespace:
        captured["provider_name"] = provider_name
        captured["max_cost_usd"] = max_cost_usd
        captured["include_reranker"] = include_reranker
        return SimpleNamespace(
            provider=provider,
            chat_runner=runner,
            reranker=reranker if include_reranker else None,
            usage_tracker=tracker,
            options=EvalRunOptions(
                mode="hosted",
                provider=provider_name,
                max_cost_usd=max_cost_usd,
            ),
        )

    monkeypatch.setattr(
        "adaptive_rag.cli.evals.get_cli_hosted_eval_runtime",
        hosted_runtime,
        raising=False,
    )

    result = CliRunner().invoke(
        app,
        [
            "evals",
            "run",
            str(suite_path),
            "--mode",
            "hosted",
            "--max-cost-usd",
            "0.05",
            "--rerank-candidate-limit",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert captured == {
        "provider_name": "qwen",
        "max_cost_usd": 0.05,
        "include_reranker": True,
    }
    assert len(reranker.requests) == 1
    data = json.loads(result.stdout)
    assert data["mode"] == "hosted"
    assert data["status"] == "passed"
    assert data["metrics"]["retrieval_hit_rate"] == 1.0
    assert data["comparison_metrics"] == {
        "dense_retrieval_hit_rate": 0.0,
        "dense_retrieval_passed_count": 0.0,
        "rerank_best_rank_delta_avg": 1.0,
        "rerank_case_improvement_count": 1.0,
        "rerank_case_regression_count": 0.0,
        "rerank_case_tie_count": 0.0,
        "rerank_retrieval_hit_rate_delta": 1.0,
        "reranked_retrieval_hit_rate": 1.0,
        "reranked_retrieval_passed_count": 1.0,
    }
    assert data["provider_usage"]["operations"][1]["operation"] == "rerank"


def test_evals_run_command_hosted_mode_rejects_invalid_rerank_limit_before_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "cli-hosted-invalid-rerank",
            "thresholds": {"retrieval_hit_rate": 1.0},
            "evidence": [
                {
                    "id": "alpha",
                    "text": "Alpha original evidence",
                    "source_type": "markdown",
                    "source_external_id": "alpha.md",
                }
            ],
            "retrieval_cases": [
                {
                    "id": "retrieve-alpha",
                    "query": "alpha",
                    "limit": 2,
                    "expected_evidence_ids": ["alpha"],
                }
            ],
            "chat_cases": [],
        },
    )

    def hosted_runtime(**_kwargs: object) -> SimpleNamespace:
        raise AssertionError("hosted runtime should not be built")

    monkeypatch.setattr(
        "adaptive_rag.cli.evals.get_cli_hosted_eval_runtime",
        hosted_runtime,
        raising=False,
    )

    result = CliRunner().invoke(
        app,
        [
            "evals",
            "run",
            str(suite_path),
            "--mode",
            "hosted",
            "--max-cost-usd",
            "0.05",
            "--rerank-candidate-limit",
            "1",
        ],
    )

    assert result.exit_code == 1
    assert (
        "rerank candidate_limit must be greater than or equal to every "
        "retrieval case limit"
    ) in result.output


def test_evals_graph_quality_gate_command_outputs_comparison_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = _make_session()
    _patch_evals_dependencies(monkeypatch, session=session)
    tracker = InMemoryProviderUsageTracker()
    provider = UsageRecordingEmbeddingProvider(
        {"Alpha original evidence": _vector(0.0)},
        tracker=tracker,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.evals.get_cli_dense_embedding_provider",
        lambda: provider,
    )
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "cli-graph-quality",
            "thresholds": {"retrieval_hit_rate": 1.0},
            "evidence": [
                {
                    "id": "alpha",
                    "text": "Alpha original evidence",
                    "source_type": "markdown",
                    "source_external_id": "alpha.md",
                    "embedding": _vector(0.0),
                },
                {
                    "id": "far",
                    "text": "Far unrelated evidence",
                    "source_type": "markdown",
                    "source_external_id": "far.md",
                    "embedding": _vector(0.9),
                },
            ],
            "retrieval_cases": [
                {
                    "id": "retrieve-alpha",
                    "query": "Alpha original evidence",
                    "limit": 2,
                    "expected_evidence_ids": ["alpha"],
                }
            ],
            "chat_cases": [],
        },
    )

    result = CliRunner().invoke(app, ["evals", "graph-quality-gate", str(suite_path)])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["suite_id"] == "cli-graph-quality"
    assert data["status"] == "passed"
    assert data["decision"] == "hold_default"
    assert data["dense_baseline"]["metrics"]["retrieval_hit_rate"] == 1.0
    assert data["graph"]["metrics"]["retrieval_hit_rate"] == 1.0
    assert data["comparison_metrics"]["graph_retrieval_hit_rate_delta"] == 0.0
    assert data["comparison_metrics"]["graph_citation_coverage"] == 1.0


def test_evals_run_command_hosted_mode_requires_budget(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session = _make_session()
    _patch_evals_dependencies(monkeypatch, session=session)
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "cli-hosted-no-budget",
            "thresholds": {},
            "evidence": [],
            "retrieval_cases": [],
            "chat_cases": [],
        },
    )

    result = CliRunner().invoke(
        app,
        ["evals", "run", str(suite_path), "--mode", "hosted"],
    )

    assert result.exit_code == 1
    assert "hosted evals require --max-cost-usd" in result.output


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
            GraphProjection.__table__,
        ],
    )
    return create_session_factory(engine)()


def _write_suite(tmp_path: Path, payload: object) -> Path:
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(json.dumps(payload), encoding="utf-8")
    return suite_path


def _vector(first: float) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = first
    return values
