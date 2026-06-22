"""Tests del quality gate M18 para retrieval graph opt-in."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

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
from adaptive_rag.evals import load_eval_suite
from adaptive_rag.evals.graph_quality_gate_runner import (
    run_graph_quality_gate_eval_suite,
    serialize_graph_quality_gate_report,
)
from adaptive_rag.graph import GraphRetrievalResult


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


class EvidenceOrderGraphRetriever:
    def __init__(
        self,
        *,
        evidence_order: Sequence[str],
        chunk_id_by_evidence_id: dict[str, UUID],
    ) -> None:
        self._rank_by_chunk_id = {
            chunk_id_by_evidence_id[evidence_id]: rank
            for rank, evidence_id in enumerate(evidence_order)
        }
        self.requests: list[dict[str, object]] = []

    def expand_project_chunks(
        self,
        *,
        project_id: UUID,
        seed_chunk_ids: Sequence[UUID],
        limit: int,
    ) -> tuple[GraphRetrievalResult, ...]:
        self.requests.append(
            {
                "project_id": project_id,
                "seed_chunk_ids": tuple(seed_chunk_ids),
                "limit": limit,
            }
        )
        ranked = sorted(
            seed_chunk_ids,
            key=lambda chunk_id: self._rank_by_chunk_id[chunk_id],
        )
        return tuple(
            GraphRetrievalResult(
                chunk_id=chunk_id,
                distance=float(index),
                score=1 / (1 + float(index)),
            )
            for index, chunk_id in enumerate(ranked[:limit])
        )


def test_graph_quality_gate_compares_dense_and_graph_with_contract_metrics(
    tmp_path: Path,
) -> None:
    suite = load_eval_suite(
        _write_suite(
            tmp_path,
            {
                "schema_version": 1,
                "suite_id": "m18-graph-quality",
                "thresholds": {"retrieval_hit_rate": 1.0},
                "evidence": [
                    {
                        "id": "alpha",
                        "text": "Alpha target evidence",
                        "source_type": "markdown",
                        "source_external_id": "alpha.md",
                        "tags": ["docs"],
                    },
                    {
                        "id": "distractor",
                        "text": "Distractor evidence",
                        "source_type": "markdown",
                        "source_external_id": "distractor.md",
                        "tags": ["docs"],
                    },
                    {
                        "id": "filtered",
                        "text": "Filtered docs evidence",
                        "source_type": "markdown",
                        "source_external_id": "filtered.md",
                        "tags": ["docs"],
                    },
                    {
                        "id": "blog",
                        "text": "Filtered blog distractor",
                        "source_type": "markdown",
                        "source_external_id": "blog.md",
                        "tags": ["blog"],
                    },
                ],
                "retrieval_cases": [
                    {
                        "id": "graph-keeps-alpha",
                        "query": "alpha query",
                        "limit": 2,
                        "expected_evidence_ids": ["alpha"],
                        "case_metadata": {
                            "intent": "graph_stability",
                            "difficulty": "medium",
                            "risk_family": "semantic_distractor",
                        },
                    },
                    {
                        "id": "graph-respects-filter",
                        "query": "filtered query",
                        "limit": 1,
                        "metadata_filter": {
                            "source_type": "markdown",
                            "tags": ["docs"],
                        },
                        "expected_evidence_ids": ["filtered"],
                        "case_metadata": {
                            "intent": "graph_filter",
                            "difficulty": "medium",
                            "risk_family": "metadata_guard",
                        },
                    },
                ],
                "chat_cases": [],
            },
        )
    )
    provider = MappingEmbeddingProvider(
        {
            "Alpha target evidence": _vector(0, 1.0),
            "Distractor evidence": _vector(0, 0.9),
            "Filtered docs evidence": _vector(1, 1.0),
            "Filtered blog distractor": _vector(1, 0.9),
            "alpha query": _vector(0, 1.0),
            "filtered query": _vector(1, 1.0),
        }
    )
    session = _make_session()

    report = run_graph_quality_gate_eval_suite(
        session,
        suite,
        provider=provider,
        graph_retriever_factory=lambda fixture_project: EvidenceOrderGraphRetriever(
            evidence_order=("alpha", "distractor", "filtered", "blog"),
            chunk_id_by_evidence_id={
                evidence_id: chunk_id
                for chunk_id, evidence_id in (
                    fixture_project.evidence_id_by_chunk_id.items()
                )
            },
        ),
    )

    assert report.status == "passed"
    assert report.dense_baseline.metrics["retrieval_hit_rate"] == 1.0
    assert report.graph.metrics["retrieval_hit_rate"] == 1.0
    assert report.comparison_metrics == {
        "dense_retrieval_hit_rate": 1.0,
        "dense_retrieval_passed_count": 2.0,
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
    }
    assert [comparison.outcome for comparison in report.comparison_cases] == [
        "tie",
        "tie",
    ]

    payload = serialize_graph_quality_gate_report(report)
    assert payload["suite_id"] == "m18-graph-quality"
    assert payload["status"] == "passed"
    assert payload["decision"] == "hold_default"
    assert payload["comparison_metrics"]["graph_citation_coverage"] == 1.0
    assert payload["comparison_metrics"]["graph_metadata_filter_passed_count"] == 1.0
    assert payload["graph"]["cases"][0]["observed_citations"][0]["source_external_id"]


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


def _vector(axis: int, value: float) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[axis] = value
    return values
