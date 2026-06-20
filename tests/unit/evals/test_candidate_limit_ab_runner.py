from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    EMBEDDING_DIMENSIONS,
    Chunk,
    Document,
    DocumentVersion,
    Project,
    Source,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.evals import EvalRunOptions, load_eval_suite
from adaptive_rag.evals.candidate_limit_runner import (
    run_candidate_limit_ab_retrieval_eval_suite,
    serialize_candidate_limit_ab_run_report,
)
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
                duration_ms=2,
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


class TargetFirstRerankProvider:
    provider_name = "qwen"
    model_name = "qwen3-rerank"

    def __init__(self, *, tracker: InMemoryProviderUsageTracker) -> None:
        self._tracker = tracker
        self.requests: list[RerankRequest] = []

    def rerank(self, request: RerankRequest) -> RerankResult:
        self.requests.append(request)
        self._tracker.record(
            ProviderCallRecord(
                provider=self.provider_name,
                model=self.model_name,
                operation="rerank",
                outcome="succeeded",
                duration_ms=5,
                usage=ProviderTokenUsage(
                    input_tokens=len(request.candidates),
                    total_tokens=len(request.candidates),
                    input_count=len(request.candidates),
                ),
                usage_source="provider_reported",
                estimated_cost_usd=0.0002,
            )
        )
        ranked = sorted(
            enumerate(request.candidates, start=1),
            key=lambda item: (
                0 if item[1].text == "Target evidence" else 1,
                item[0],
            ),
        )
        return RerankResult(
            provider_name=self.provider_name,
            model_name=self.model_name,
            scores=tuple(
                RerankScore(
                    candidate_id=candidate.candidate_id,
                    score=1.0 if candidate.text == "Target evidence" else 0.1,
                    original_rank=original_rank,
                    rerank_rank=rerank_rank,
                )
                for rerank_rank, (original_rank, candidate) in enumerate(
                    ranked[: request.top_k],
                    start=1,
                )
            ),
        )


class ScenarioRerankProvider:
    provider_name = "qwen"
    model_name = "qwen3-rerank"

    def __init__(self, *, tracker: InMemoryProviderUsageTracker) -> None:
        self._tracker = tracker

    def rerank(self, request: RerankRequest) -> RerankResult:
        self._tracker.record(
            ProviderCallRecord(
                provider=self.provider_name,
                model=self.model_name,
                operation="rerank",
                outcome="succeeded",
                duration_ms=5,
                usage=ProviderTokenUsage(
                    input_tokens=len(request.candidates),
                    total_tokens=len(request.candidates),
                    input_count=len(request.candidates),
                ),
                usage_source="provider_reported",
                estimated_cost_usd=0.0002,
            )
        )
        ranked = sorted(
            enumerate(request.candidates, start=1),
            key=lambda item: (_scenario_priority(request.query, item[1].text), item[0]),
        )
        return RerankResult(
            provider_name=self.provider_name,
            model_name=self.model_name,
            scores=tuple(
                RerankScore(
                    candidate_id=candidate.candidate_id,
                    score=1.0 if rerank_rank == 1 else 0.1,
                    original_rank=original_rank,
                    rerank_rank=rerank_rank,
                )
                for rerank_rank, (original_rank, candidate) in enumerate(
                    ranked[: request.top_k],
                    start=1,
                )
            ),
        )


def test_candidate_limit_ab_runner_serializes_quality_cost_and_regressions(
    tmp_path: Path,
) -> None:
    suite = load_eval_suite(
        _write_suite(
            tmp_path,
            {
                "schema_version": 1,
                "suite_id": "candidate-limit-ab",
                "thresholds": {"retrieval_hit_rate": 1.0},
                "evidence": [
                    {
                        "id": "target",
                        "text": "Target evidence",
                        "source_type": "markdown",
                        "source_external_id": "target.md",
                    },
                    {
                        "id": "distractor",
                        "text": "Distractor evidence",
                        "source_type": "markdown",
                        "source_external_id": "distractor.md",
                    },
                    {
                        "id": "far",
                        "text": "Far evidence",
                        "source_type": "markdown",
                        "source_external_id": "far.md",
                    },
                ],
                "retrieval_cases": [
                    {
                        "id": "target-query",
                        "query": "target query",
                        "limit": 1,
                        "expected_evidence_ids": ["target"],
                        "case_metadata": {
                            "intent": "rerank_helpful",
                            "difficulty": "medium",
                            "risk_family": "semantic_distractor",
                        },
                    }
                ],
                "chat_cases": [],
            },
        )
    )
    tracker = InMemoryProviderUsageTracker()
    provider = UsageRecordingEmbeddingProvider(
        {
            "Target evidence": _vector(0.2),
            "Distractor evidence": _vector(0.1),
            "Far evidence": _vector(0.9),
            "target query": _vector(0.0),
        },
        tracker=tracker,
    )
    reranker = TargetFirstRerankProvider(tracker=tracker)

    report = run_candidate_limit_ab_retrieval_eval_suite(
        _make_session(),
        suite,
        provider=provider,
        reranker=reranker,
        candidate_limits=(2, 1),
        usage_tracker=tracker,
        options=EvalRunOptions(mode="hosted", provider="qwen", max_cost_usd=0.05),
    )

    assert provider.inputs == [
        "Target evidence",
        "Distractor evidence",
        "Far evidence",
        "target query",
        "target query",
        "target query",
    ]
    assert [len(request.candidates) for request in reranker.requests] == [1, 2]
    assert report.dense_baseline.metrics["retrieval_hit_rate"] == 0.0
    assert [row.candidate_limit for row in report.rows] == [1, 2]
    assert report.rows[0].status == "failed"
    assert report.rows[0].comparison_metrics["rerank_case_tie_count"] == 1.0
    assert report.rows[1].status == "passed"
    assert report.rows[1].comparison_metrics["rerank_case_improvement_count"] == 1.0
    assert report.rows[1].outcome_counts_by_intent == {
        "rerank_helpful": {"improvement": 1, "regression": 0, "tie": 0}
    }
    assert report.rows[1].outcome_counts_by_difficulty == {
        "medium": {"improvement": 1, "regression": 0, "tie": 0}
    }
    assert report.rows[1].outcome_counts_by_risk_family == {
        "semantic_distractor": {"regression": 0, "improvement": 1, "tie": 0}
    }

    payload = serialize_candidate_limit_ab_run_report(report)
    assert payload["mode"] == "hosted"
    assert payload["dense_baseline"]["metrics"] == {
        "retrieval_case_count": 1.0,
        "retrieval_hit_rate": 0.0,
        "retrieval_passed_count": 0.0,
    }
    assert payload["rows"][0]["provider_usage"]["operations"] == [
        {
            "operation": "embedding",
            "provider": "qwen",
            "model": "text-embedding-v4",
            "call_count": 1,
            "succeeded_count": 1,
            "failed_count": 0,
            "blocked_count": 0,
            "input_tokens": 2,
            "output_tokens": None,
            "total_tokens": 2,
            "input_count": 1,
            "estimated_cost_usd": 0.0001,
            "usage_unavailable_count": 0,
        },
        {
            "operation": "rerank",
            "provider": "qwen",
            "model": "qwen3-rerank",
            "call_count": 1,
            "succeeded_count": 1,
            "failed_count": 0,
            "blocked_count": 0,
            "input_tokens": 1,
            "output_tokens": None,
            "total_tokens": 1,
            "input_count": 1,
            "estimated_cost_usd": 0.0002,
            "usage_unavailable_count": 0,
        },
    ]
    assert payload["rows"][1]["comparison_cases"] == [
        {
            "id": "target-query",
            "outcome": "improvement",
            "dense_status": "failed",
            "reranked_status": "passed",
            "dense_best_rank": 0.0,
            "reranked_best_rank": 1.0,
            "best_rank_delta": 1.0,
            "dense_observed_evidence_ids": ["distractor"],
            "reranked_observed_evidence_ids": ["target"],
            "gained_evidence_ids": ["target"],
            "lost_evidence_ids": [],
        }
    ]
    assert payload["provider_usage"]["total_call_count"] == 6


def test_candidate_limit_ab_runner_reports_gap_groups_and_regressions_first(
    tmp_path: Path,
) -> None:
    suite = load_eval_suite(
        _write_suite(
            tmp_path,
            {
                "schema_version": 1,
                "suite_id": "candidate-limit-gaps",
                "thresholds": {"retrieval_hit_rate": 0.5},
                "evidence": [
                    {
                        "id": "alpha",
                        "text": "Alpha target evidence",
                        "source_type": "markdown",
                        "source_external_id": "alpha.md",
                    },
                    {
                        "id": "alpha-distractor",
                        "text": "Alpha distractor evidence",
                        "source_type": "markdown",
                        "source_external_id": "alpha-distractor.md",
                    },
                    {
                        "id": "stable",
                        "text": "Stable target evidence",
                        "source_type": "markdown",
                        "source_external_id": "stable.md",
                    },
                    {
                        "id": "stable-distractor",
                        "text": "Stable distractor evidence",
                        "source_type": "markdown",
                        "source_external_id": "stable-distractor.md",
                    },
                    {
                        "id": "regression",
                        "text": "Regression target evidence",
                        "source_type": "markdown",
                        "source_external_id": "regression.md",
                    },
                    {
                        "id": "regression-distractor",
                        "text": "Regression distractor evidence",
                        "source_type": "markdown",
                        "source_external_id": "regression-distractor.md",
                    },
                ],
                "retrieval_cases": [
                    {
                        "id": "rerank-improves-alpha",
                        "query": "alpha scenario query",
                        "limit": 1,
                        "expected_evidence_ids": ["alpha"],
                        "case_metadata": {
                            "intent": "rerank_helpful",
                            "difficulty": "medium",
                            "risk_family": "semantic_distractor",
                        },
                    },
                    {
                        "id": "rerank-keeps-stable",
                        "query": "stable scenario query",
                        "limit": 1,
                        "expected_evidence_ids": ["stable"],
                        "case_metadata": {
                            "intent": "rerank_stable",
                            "difficulty": "easy",
                            "risk_family": "rerank_regression",
                        },
                    },
                    {
                        "id": "rerank-regresses-target",
                        "query": "regression scenario query",
                        "limit": 1,
                        "expected_evidence_ids": ["regression"],
                        "case_metadata": {
                            "intent": "rerank_stable",
                            "difficulty": "hard",
                            "risk_family": "rerank_regression",
                        },
                    },
                ],
                "chat_cases": [],
            },
        )
    )
    tracker = InMemoryProviderUsageTracker()
    provider = UsageRecordingEmbeddingProvider(
        {
            "Alpha target evidence": _scenario_vector(0, 0.8),
            "Alpha distractor evidence": _scenario_vector(0, 0.9),
            "Stable target evidence": _scenario_vector(1, 1.0),
            "Stable distractor evidence": _scenario_vector(1, 0.5),
            "Regression target evidence": _scenario_vector(2, 1.0),
            "Regression distractor evidence": _scenario_vector(2, 0.5),
            "alpha scenario query": _scenario_vector(0, 1.0),
            "stable scenario query": _scenario_vector(1, 1.0),
            "regression scenario query": _scenario_vector(2, 1.0),
        },
        tracker=tracker,
    )

    report = run_candidate_limit_ab_retrieval_eval_suite(
        _make_session(),
        suite,
        provider=provider,
        reranker=ScenarioRerankProvider(tracker=tracker),
        candidate_limits=(2,),
        usage_tracker=tracker,
        options=EvalRunOptions(mode="hosted", provider="qwen", max_cost_usd=0.05),
    )

    row = report.rows[0]
    assert row.outcome_counts_by_risk_family == {
        "rerank_regression": {"regression": 1, "improvement": 0, "tie": 1},
        "semantic_distractor": {"regression": 0, "improvement": 1, "tie": 0},
    }

    payload = serialize_candidate_limit_ab_run_report(report)
    assert payload["rows"][0]["outcome_counts_by_risk_family"] == {
        "rerank_regression": {"regression": 1, "improvement": 0, "tie": 1},
        "semantic_distractor": {"regression": 0, "improvement": 1, "tie": 0},
    }
    assert [
        comparison["id"] for comparison in payload["rows"][0]["comparison_cases"]
    ] == [
        "rerank-regresses-target",
        "rerank-improves-alpha",
        "rerank-keeps-stable",
    ]
    assert payload["rows"][0]["comparison_cases"][0]["lost_evidence_ids"] == [
        "regression"
    ]


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


def _vector(first: float) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = first
    return values


def _scenario_vector(axis: int, value: float) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[axis] = value
    return values


def _scenario_priority(query: str, text: str) -> int:
    if "alpha" in query:
        return 0 if text == "Alpha target evidence" else 1
    if "stable" in query:
        return 0 if text == "Stable target evidence" else 1
    if "regression" in query:
        return 0 if text == "Regression distractor evidence" else 1
    return 1
