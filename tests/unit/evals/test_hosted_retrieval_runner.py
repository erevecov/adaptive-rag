"""Tests del runner hosted de retrieval para evals M8."""

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
from adaptive_rag.evals import EvalRunOptions, load_eval_suite, serialize_eval_report
from adaptive_rag.evals.hosted import run_hosted_retrieval_eval_suite
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


def test_run_hosted_retrieval_eval_suite_reports_usage_and_quality(
    tmp_path: Path,
) -> None:
    suite = load_eval_suite(
        _write_suite(
            tmp_path,
            {
                "schema_version": 1,
                "suite_id": "hosted-retrieval",
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
                        "id": "retrieve-alpha",
                        "query": "Alpha original evidence",
                        "limit": 2,
                        "expected_evidence_ids": ["alpha"],
                    }
                ],
                "chat_cases": [],
            },
        )
    )
    tracker = InMemoryProviderUsageTracker()
    provider = UsageRecordingEmbeddingProvider(
        {
            "Alpha original evidence": _vector(0.0),
            "Far unrelated evidence": _vector(0.9),
        },
        tracker=tracker,
    )

    report = run_hosted_retrieval_eval_suite(
        _make_session(),
        suite,
        provider=provider,
        usage_tracker=tracker,
        options=EvalRunOptions(mode="hosted", provider="qwen", max_cost_usd=0.05),
    )

    assert provider.inputs == [
        "Alpha original evidence",
        "Far unrelated evidence",
        "Alpha original evidence",
    ]
    assert report.mode == "hosted"
    assert report.status == "passed"
    assert report.metrics["retrieval_hit_rate"] == 1.0
    assert report.cases[0].observed_evidence_ids == ("alpha", "far")

    payload = serialize_eval_report(report)
    assert payload["mode"] == "hosted"
    assert payload["provider_usage"] == {
        "total_call_count": 2,
        "total_estimated_cost_usd": 0.0003,
        "operations": [
            {
                "operation": "embedding",
                "provider": "qwen",
                "model": "text-embedding-v4",
                "call_count": 2,
                "succeeded_count": 2,
                "failed_count": 0,
                "blocked_count": 0,
                "input_tokens": 9,
                "output_tokens": None,
                "total_tokens": 9,
                "input_count": 3,
                "estimated_cost_usd": 0.0003,
                "usage_unavailable_count": 0,
            }
        ],
    }


def test_run_hosted_retrieval_eval_suite_compares_dense_and_reranked_quality(
    tmp_path: Path,
) -> None:
    suite = load_eval_suite(
        _write_suite(
            tmp_path,
            {
                "schema_version": 1,
                "suite_id": "hosted-rerank-retrieval",
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
    reranker = UsageRecordingRerankProvider(tracker=tracker)

    report = run_hosted_retrieval_eval_suite(
        _make_session(),
        suite,
        provider=provider,
        reranker=reranker,
        rerank_candidate_limit=2,
        usage_tracker=tracker,
        options=EvalRunOptions(mode="hosted", provider="qwen", max_cost_usd=0.05),
    )

    assert provider.inputs == [
        "Alpha original evidence",
        "Beta distractor evidence",
        "Which text answers alpha?",
        "Which text answers alpha?",
    ]
    assert len(reranker.requests) == 1
    assert [candidate.text for candidate in reranker.requests[0].candidates] == [
        "Beta distractor evidence",
        "Alpha original evidence",
    ]
    assert report.mode == "hosted"
    assert report.status == "passed"
    assert report.metrics["retrieval_hit_rate"] == 1.0
    assert report.comparison_metrics == {
        "dense_retrieval_hit_rate": 0.0,
        "dense_retrieval_passed_count": 0.0,
        "rerank_retrieval_hit_rate_delta": 1.0,
        "reranked_retrieval_hit_rate": 1.0,
        "reranked_retrieval_passed_count": 1.0,
    }
    assert report.cases[0].observed_evidence_ids == ("alpha",)

    payload = serialize_eval_report(report)
    assert payload["comparison_metrics"] == {
        "dense_retrieval_hit_rate": 0.0,
        "dense_retrieval_passed_count": 0.0,
        "rerank_retrieval_hit_rate_delta": 1.0,
        "reranked_retrieval_hit_rate": 1.0,
        "reranked_retrieval_passed_count": 1.0,
    }
    assert payload["provider_usage"]["operations"] == [
        {
            "operation": "embedding",
            "provider": "qwen",
            "model": "text-embedding-v4",
            "call_count": 3,
            "succeeded_count": 3,
            "failed_count": 0,
            "blocked_count": 0,
            "input_tokens": 14,
            "output_tokens": None,
            "total_tokens": 14,
            "input_count": 4,
            "estimated_cost_usd": 0.0004,
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
            "input_tokens": 10,
            "output_tokens": None,
            "total_tokens": 10,
            "input_count": 2,
            "estimated_cost_usd": 0.0002,
            "usage_unavailable_count": 0,
        },
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

