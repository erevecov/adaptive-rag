"""Tests for the M31 retrieval strategy gate."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    EMBEDDING_DIMENSIONS,
    Chunk,
    ChunkSparseEmbedding,
    Document,
    DocumentVersion,
    GraphProjection,
    Project,
    Source,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.evals import load_eval_suite
from adaptive_rag.evals.strategy_gate_runner import (
    run_retrieval_strategy_gate_eval_suite,
    serialize_retrieval_strategy_gate_report,
)


class MappingEmbeddingProvider:
    provider_name = "fake"
    model_name = "eval-mapping-v1"
    dimensions = EMBEDDING_DIMENSIONS

    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self._mapping = mapping
        self.inputs: list[str] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.inputs.extend(texts)
        return [list(self._mapping[text]) for text in texts]


def test_strategy_gate_compares_ready_modes_and_keeps_dense_default(
    tmp_path: Path,
) -> None:
    suite = load_eval_suite(
        _write_suite(
            tmp_path,
            {
                "schema_version": 1,
                "suite_id": "strategy-gate-ready",
                "thresholds": {"retrieval_hit_rate": 1.0},
                "evidence": [
                    {
                        "id": "alpha",
                        "text": "Alpha exact policy evidence",
                        "source_type": "markdown",
                        "source_external_id": "alpha.md",
                        "tags": ["docs"],
                    },
                    {
                        "id": "export",
                        "text": "Admin export route is /v1/admin/exports/{export_id}",
                        "source_type": "markdown",
                        "source_external_id": "export.md",
                        "tags": ["docs"],
                    },
                    {
                        "id": "blog",
                        "text": "Blog copy mentions exports without route identifiers",
                        "source_type": "markdown",
                        "source_external_id": "blog.md",
                        "tags": ["blog"],
                    },
                ],
                "retrieval_cases": [
                    {
                        "id": "retrieve-alpha",
                        "query": "Alpha exact policy evidence",
                        "limit": 2,
                        "expected_evidence_ids": ["alpha"],
                    },
                    {
                        "id": "retrieve-export-filtered",
                        "query": "Which admin export route includes export_id?",
                        "limit": 1,
                        "metadata_filter": {
                            "source_type": "markdown",
                            "tags": ["docs"],
                        },
                        "expected_evidence_ids": ["export"],
                    },
                ],
                "chat_cases": [],
            },
        )
    )
    provider = MappingEmbeddingProvider(
        {
            "Alpha exact policy evidence": _axis_vector(0),
            "Admin export route is /v1/admin/exports/{export_id}": _axis_vector(1),
            "Blog copy mentions exports without route identifiers": _axis_vector(2),
            "Which admin export route includes export_id?": _axis_vector(1),
        }
    )

    report = run_retrieval_strategy_gate_eval_suite(
        _make_session(),
        suite,
        provider=provider,
        strategies=(
            "dense",
            "lexical",
            "hybrid_rrf",
            "dense_sparse",
            "graph",
            "dense_rerank",
        ),
    )

    assert report.status == "passed"
    assert report.default_strategy == "dense"
    assert report.recommended_default == "dense"
    assert report.dense_baseline.metrics["retrieval_hit_rate"] == 1.0
    decisions = {row.strategy: row.decision for row in report.rows}
    assert decisions == {
        "dense": "promote",
        "lexical": "keep_opt_in",
        "hybrid_rrf": "keep_opt_in",
        "dense_sparse": "keep_opt_in",
        "graph": "hold",
        "dense_rerank": "keep_opt_in",
    }

    payload = serialize_retrieval_strategy_gate_report(report)
    assert payload["suite_id"] == "strategy-gate-ready"
    assert payload["status"] == "passed"
    assert payload["default_strategy"] == "dense"
    assert payload["recommended_default"] == "dense"
    assert payload["strategy_decisions"] == [
        {
            "strategy": "dense",
            "status": "passed",
            "decision": "promote",
            "reason": "dense baseline passes and remains the recommended default",
            "metrics": {
                "retrieval_case_count": 2.0,
                "retrieval_hit_rate": 1.0,
                "retrieval_passed_count": 2.0,
            },
            "comparison_metrics": {},
        },
        {
            "strategy": "lexical",
            "status": "passed",
            "decision": "keep_opt_in",
            "reason": "lexical matches dense without regressions",
            "metrics": {
                "retrieval_case_count": 2.0,
                "retrieval_hit_rate": 1.0,
                "retrieval_passed_count": 2.0,
            },
            "comparison_metrics": {
                "lexical_best_rank_delta_avg": 0.0,
                "lexical_case_improvement_count": 0.0,
                "lexical_case_regression_count": 0.0,
                "lexical_case_tie_count": 2.0,
                "lexical_citation_coverage": 1.0,
                "lexical_metadata_filter_case_count": 1.0,
                "lexical_metadata_filter_passed_count": 1.0,
                "lexical_provider_cost_delta_usd": 0.0,
                "lexical_retrieval_hit_rate": 1.0,
                "lexical_retrieval_hit_rate_delta": 0.0,
                "lexical_retrieval_passed_count": 2.0,
            },
        },
        {
            "strategy": "hybrid_rrf",
            "status": "passed",
            "decision": "keep_opt_in",
            "reason": "hybrid_rrf matches dense without regressions",
            "metrics": {
                "retrieval_case_count": 2.0,
                "retrieval_hit_rate": 1.0,
                "retrieval_passed_count": 2.0,
            },
            "comparison_metrics": {
                "hybrid_rrf_best_rank_delta_avg": 0.0,
                "hybrid_rrf_case_improvement_count": 0.0,
                "hybrid_rrf_case_regression_count": 0.0,
                "hybrid_rrf_case_tie_count": 2.0,
                "hybrid_rrf_citation_coverage": 1.0,
                "hybrid_rrf_metadata_filter_case_count": 1.0,
                "hybrid_rrf_metadata_filter_passed_count": 1.0,
                "hybrid_rrf_provider_cost_delta_usd": 0.0,
                "hybrid_rrf_retrieval_hit_rate": 1.0,
                "hybrid_rrf_retrieval_hit_rate_delta": 0.0,
                "hybrid_rrf_retrieval_passed_count": 2.0,
            },
        },
        {
            "strategy": "dense_sparse",
            "status": "passed",
            "decision": "keep_opt_in",
            "reason": "dense_sparse matches dense without regressions",
            "metrics": {
                "retrieval_case_count": 2.0,
                "retrieval_hit_rate": 1.0,
                "retrieval_passed_count": 2.0,
            },
            "comparison_metrics": {
                "dense_sparse_best_rank_delta_avg": 0.0,
                "dense_sparse_case_improvement_count": 0.0,
                "dense_sparse_case_regression_count": 0.0,
                "dense_sparse_case_tie_count": 2.0,
                "dense_sparse_citation_coverage": 1.0,
                "dense_sparse_metadata_filter_case_count": 1.0,
                "dense_sparse_metadata_filter_passed_count": 1.0,
                "dense_sparse_provider_cost_delta_usd": 0.0,
                "dense_sparse_retrieval_hit_rate": 1.0,
                "dense_sparse_retrieval_hit_rate_delta": 0.0,
                "dense_sparse_retrieval_passed_count": 2.0,
            },
        },
        {
            "strategy": "graph",
            "status": "passed",
            "decision": "hold",
            "reason": (
                "graph passes the offline quality contract but still requires "
                "live operational evidence before promotion"
            ),
            "metrics": {
                "retrieval_case_count": 2.0,
                "retrieval_hit_rate": 1.0,
                "retrieval_passed_count": 2.0,
            },
            "comparison_metrics": {
                "graph_best_rank_delta_avg": 0.0,
                "graph_case_improvement_count": 0.0,
                "graph_case_regression_count": 0.0,
                "graph_case_tie_count": 2.0,
                "graph_citation_coverage": 1.0,
                "graph_metadata_filter_case_count": 1.0,
                "graph_metadata_filter_passed_count": 1.0,
                "graph_provider_cost_delta_usd": 0.0,
                "graph_retrieval_hit_rate": 1.0,
                "graph_retrieval_hit_rate_delta": 0.0,
                "graph_retrieval_passed_count": 2.0,
            },
        },
        {
            "strategy": "dense_rerank",
            "status": "passed",
            "decision": "keep_opt_in",
            "reason": "dense_rerank matches dense without regressions",
            "metrics": {
                "retrieval_case_count": 2.0,
                "retrieval_hit_rate": 1.0,
                "retrieval_passed_count": 2.0,
            },
            "comparison_metrics": {
                "dense_rerank_best_rank_delta_avg": 0.0,
                "dense_rerank_case_improvement_count": 0.0,
                "dense_rerank_case_regression_count": 0.0,
                "dense_rerank_case_tie_count": 2.0,
                "dense_rerank_citation_coverage": 1.0,
                "dense_rerank_metadata_filter_case_count": 1.0,
                "dense_rerank_metadata_filter_passed_count": 1.0,
                "dense_rerank_provider_cost_delta_usd": 0.0,
                "dense_rerank_retrieval_hit_rate": 1.0,
                "dense_rerank_retrieval_hit_rate_delta": 0.0,
                "dense_rerank_retrieval_passed_count": 2.0,
            },
        },
    ]


def test_strategy_gate_marks_contextual_dense_needs_more_data_without_summaries(
    tmp_path: Path,
) -> None:
    suite = load_eval_suite(
        _write_suite(
            tmp_path,
            {
                "schema_version": 1,
                "suite_id": "strategy-gate-no-context",
                "thresholds": {"retrieval_hit_rate": 1.0},
                "evidence": [
                    {
                        "id": "alpha",
                        "text": "Alpha exact policy evidence",
                        "source_type": "markdown",
                        "source_external_id": "alpha.md",
                    }
                ],
                "retrieval_cases": [
                    {
                        "id": "retrieve-alpha",
                        "query": "Alpha exact policy evidence",
                        "expected_evidence_ids": ["alpha"],
                    }
                ],
                "chat_cases": [],
            },
        )
    )

    report = run_retrieval_strategy_gate_eval_suite(
        _make_session(),
        suite,
        strategies=("contextual_dense",),
    )

    row = report.rows[0]
    assert row.strategy == "contextual_dense"
    assert row.status == "skipped"
    assert row.decision == "needs_more_data"
    assert row.reason == (
        "contextual_dense requires eval evidence with contextual_summary values"
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
            ChunkSparseEmbedding.__table__,
            GraphProjection.__table__,
        ],
    )
    return create_session_factory(engine)()


def _write_suite(tmp_path: Path, payload: object) -> Path:
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(json.dumps(payload), encoding="utf-8")
    return suite_path


def _axis_vector(axis: int) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[axis] = 1.0
    return values
