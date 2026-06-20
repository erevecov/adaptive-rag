"""Tests del runner offline de retrieval para evals M6."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
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
from adaptive_rag.evals import load_eval_suite, serialize_eval_report
from adaptive_rag.evals.retrieval_runner import run_retrieval_eval_suite


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


def test_run_retrieval_eval_suite_passes_repo_smoke_fixture() -> None:
    suite = load_eval_suite(
        _repo_root() / "evals" / "fixtures" / "retrieval-smoke.json"
    )
    provider = MappingEmbeddingProvider(
        {
            "Alpha original evidence": _vector(0.0),
            "Far unrelated evidence": _vector(0.9),
        }
    )
    session = _make_session()

    report = run_retrieval_eval_suite(session, suite, provider=provider)

    assert provider.inputs == [
        "Alpha original evidence",
        "Far unrelated evidence",
        "Alpha original evidence",
    ]
    assert report.status == "passed"
    assert report.metrics == {
        "retrieval_case_count": 1.0,
        "retrieval_hit_rate": 1.0,
        "retrieval_passed_count": 1.0,
    }
    assert report.thresholds == {"retrieval_hit_rate": 1.0}
    assert len(report.cases) == 1
    case = report.cases[0]
    assert case.id == "retrieve-alpha"
    assert case.kind == "retrieval"
    assert case.status == "passed"
    assert case.case_metadata is not None
    assert case.case_metadata.intent == "exact_match"
    assert case.case_metadata.difficulty == "easy"
    assert case.case_metadata.coverage_notes == ("baseline dense smoke",)
    assert case.metrics == {
        "best_rank": 1.0,
        "expected_count": 1.0,
        "hit": 1.0,
        "matched_count": 1.0,
        "missing_count": 0.0,
        "retrieved_count": 2.0,
    }
    assert case.errors == ()
    assert case.observed_evidence_ids == ("alpha", "far")
    assert len(case.observed_citations) == 2
    assert case.observed_citations[0].evidence_id == "alpha"
    assert case.observed_citations[0].rank == 1
    assert case.observed_citations[0].source_external_id == "alpha.md"
    assert case.observed_citations[0].snippet == "Alpha original evidence"

    assert serialize_eval_report(report)["cases"][0]["observed_citations"][0] == {
        "evidence_id": "alpha",
        "chunk_id": case.observed_citations[0].chunk_id,
        "rank": 1,
        "score": pytest.approx(1.0),
        "source_external_id": "alpha.md",
        "snippet": "Alpha original evidence",
    }


def test_run_retrieval_eval_suite_passes_repo_dataset_pack_fixture() -> None:
    suite = load_eval_suite(
        _repo_root() / "evals" / "fixtures" / "retrieval-dataset-pack.json"
    )
    provider = MappingEmbeddingProvider(_dataset_pack_embeddings())
    session = _make_session()

    report = run_retrieval_eval_suite(session, suite, provider=provider)

    assert report.status == "passed"
    assert report.metrics == {
        "retrieval_case_count": 7.0,
        "retrieval_hit_rate": 1.0,
        "retrieval_passed_count": 7.0,
    }
    assert tuple(case.id for case in report.cases) == (
        "exact-api-error-fields",
        "paraphrase-invoice-export",
        "distractor-alpha-release-notes",
        "metadata-filter-docs-only",
        "multi-evidence-quality-gate",
        "rerank-helpful-candidate",
        "rerank-stable-exact",
    )
    assert all(case.metrics["missing_count"] == 0.0 for case in report.cases)

    by_case = {case.id: case for case in report.cases}
    assert by_case["metadata-filter-docs-only"].observed_evidence_ids == (
        "metadata-docs",
    )
    assert by_case["multi-evidence-quality-gate"].metrics["expected_count"] == 2.0
    assert by_case["multi-evidence-quality-gate"].metrics["matched_count"] == 2.0
    assert set(by_case["multi-evidence-quality-gate"].observed_evidence_ids) >= {
        "latency-metric",
        "cost-metric",
    }
    assert by_case["rerank-helpful-candidate"].case_metadata is not None
    assert by_case["rerank-helpful-candidate"].case_metadata.intent == (
        "rerank_helpful"
    )
    assert by_case["rerank-stable-exact"].case_metadata is not None
    assert by_case["rerank-stable-exact"].case_metadata.intent == "rerank_stable"


def test_run_retrieval_eval_suite_reports_missing_expected_evidence(
    tmp_path: Path,
) -> None:
    suite = load_eval_suite(
        _write_suite(
            tmp_path,
            {
                "schema_version": 1,
                "suite_id": "retrieval-fail",
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
                        "case_metadata": {
                            "intent": "paraphrase",
                            "difficulty": "medium",
                            "coverage_notes": [
                                "dense should not lose alpha to a distractor"
                            ],
                        },
                        "expected_evidence_ids": ["alpha"],
                    }
                ],
                "chat_cases": [],
            }
        )
    )
    provider = MappingEmbeddingProvider(
        {
            "Alpha original evidence": _vector(0.9),
            "Far unrelated evidence": _vector(0.0),
        }
    )
    session = _make_session()

    report = run_retrieval_eval_suite(session, suite, provider=provider)

    assert report.status == "failed"
    assert report.metrics["retrieval_hit_rate"] == 0.0
    assert report.cases[0].status == "failed"
    assert report.cases[0].metrics["hit"] == 0.0
    assert report.cases[0].metrics["missing_count"] == 1.0
    assert report.cases[0].observed_evidence_ids == ("far",)
    assert report.cases[0].errors == ("missing expected evidence: alpha",)
    assert serialize_eval_report(report)["cases"][0]["case_metadata"] == {
        "coverage_notes": ["dense should not lose alpha to a distractor"],
        "difficulty": "medium",
        "intent": "paraphrase",
    }


def test_run_retrieval_eval_suite_uses_declared_metadata_filters(
    tmp_path: Path,
) -> None:
    suite = load_eval_suite(
        _write_suite(
            tmp_path,
            {
                "schema_version": 1,
                "suite_id": "retrieval-filter",
                "thresholds": {"retrieval_hit_rate": 1.0},
                "evidence": [
                    {
                        "id": "alpha",
                        "text": "Alpha docs evidence",
                        "source_type": "markdown",
                        "source_external_id": "alpha.md",
                        "tags": ["docs"],
                    },
                    {
                        "id": "blog",
                        "text": "Blog evidence",
                        "source_type": "markdown",
                        "source_external_id": "blog.md",
                        "tags": ["blog"],
                    },
                ],
                "retrieval_cases": [
                    {
                        "id": "retrieve-filtered",
                        "query": "Blog evidence",
                        "limit": 1,
                        "metadata_filter": {
                            "source_type": "markdown",
                            "tags": ["docs"],
                        },
                        "expected_evidence_ids": ["alpha"],
                    }
                ],
                "chat_cases": [],
            }
        )
    )
    provider = MappingEmbeddingProvider(
        {
            "Alpha docs evidence": _vector(0.9),
            "Blog evidence": _vector(0.0),
        }
    )
    session = _make_session()

    report = run_retrieval_eval_suite(session, suite, provider=provider)

    assert report.status == "passed"
    assert report.cases[0].observed_evidence_ids == ("alpha",)
    assert report.cases[0].metrics["hit"] == 1.0


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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _vector(first: float) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = first
    return values


def _axis_vector(axis: int) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[axis] = 1.0
    return values


def _dataset_pack_embeddings() -> dict[str, list[float]]:
    return {
        "Alpha API errors must include a stable code, message, and request id.": (
            _axis_vector(0)
        ),
        "Alpha API release notes list dashboard color and navigation changes.": (
            _axis_vector(1)
        ),
        "Billing policy allows invoices to be exported after payment settlement.": (
            _axis_vector(2)
        ),
        "Marketing blog discusses payment themes without export requirements.": (
            _axis_vector(3)
        ),
        "Metadata filters should keep public docs separate from blog posts.": (
            _axis_vector(4)
        ),
        "A blog draft repeats metadata filter terms but is not authoritative.": (
            _axis_vector(5)
        ),
        "Retrieval latency analysis requires p50 and p95 measurements.": (
            _axis_vector(6)
        ),
        "Retrieval cost analysis requires provider token and rerank usage totals.": (
            _axis_vector(6)
        ),
        (
            "Rerank can promote citation policy answers when dense recall "
            "returns a close candidate."
        ): _axis_vector(7),
        (
            "Rerank should keep exact policy evidence first when dense rank "
            "is already correct."
        ): _axis_vector(8),
        "What fields must Alpha API errors include?": _axis_vector(0),
        "Can users download invoices once a payment has settled?": _axis_vector(2),
        "Which Alpha item describes error response fields, not release note timing?": (
            _axis_vector(0)
        ),
        "Which public metadata filter guidance should be used?": _axis_vector(5),
        "What measurements are required to evaluate retrieval latency and cost?": (
            _axis_vector(6)
        ),
        "Which candidate should rerank promote for citation policy answers?": (
            _axis_vector(7)
        ),
        (
            "Which evidence should stay first when dense ranking already found "
            "the exact policy?"
        ): _axis_vector(8),
    }
