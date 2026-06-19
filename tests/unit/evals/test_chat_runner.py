"""Tests del runner offline de chat para evals M6."""

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
from adaptive_rag.evals import (
    load_eval_suite,
    run_chat_eval_suite,
    serialize_eval_report,
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


def test_run_chat_eval_suite_passes_repo_smoke_fixture() -> None:
    suite = load_eval_suite(
        _repo_root() / "evals" / "fixtures" / "chat-smoke.json"
    )
    provider = MappingEmbeddingProvider(
        {
            "Alpha original evidence": _vector(0.0),
            "Far unrelated evidence": _vector(0.9),
        }
    )
    session = _make_session()

    report = run_chat_eval_suite(session, suite, provider=provider)

    assert provider.inputs == [
        "Alpha original evidence",
        "Far unrelated evidence",
        "Alpha original evidence",
    ]
    assert report.status == "passed"
    assert report.metrics == {
        "chat_case_count": 1.0,
        "chat_citation_coverage": 1.0,
        "chat_passed_count": 1.0,
    }
    assert report.thresholds == {"chat_citation_coverage": 1.0}
    assert len(report.cases) == 1
    case = report.cases[0]
    assert case.id == "chat-alpha"
    assert case.kind == "chat"
    assert case.status == "passed"
    assert case.metrics == {
        "citation_coverage": 1.0,
        "cited_count": 2.0,
        "expected_count": 1.0,
        "matched_count": 1.0,
        "tool_call_count": 1.0,
        "tool_query_match": 1.0,
    }
    assert case.errors == ()
    assert case.observed_evidence_ids == ("alpha", "far")
    assert case.observed_tool_queries == ("Alpha original evidence",)
    assert len(case.observed_citations) == 2
    assert case.observed_citations[0].evidence_id == "alpha"
    assert case.observed_citations[0].rank == 1
    assert case.observed_citations[0].source_external_id == "alpha.md"
    assert case.observed_citations[0].snippet == "Alpha original evidence"

    assert serialize_eval_report(report)["cases"][0]["observed_tool_queries"] == [
        "Alpha original evidence"
    ]
    assert serialize_eval_report(report)["cases"][0]["observed_citations"][0] == {
        "evidence_id": "alpha",
        "chunk_id": case.observed_citations[0].chunk_id,
        "rank": 1,
        "score": pytest.approx(1.0),
        "source_external_id": "alpha.md",
        "snippet": "Alpha original evidence",
    }


def test_run_chat_eval_suite_reports_missing_expected_evidence(
    tmp_path: Path,
) -> None:
    suite = load_eval_suite(
        _write_suite(
            tmp_path,
            {
                "schema_version": 1,
                "suite_id": "chat-missing-evidence",
                "thresholds": {"chat_citation_coverage": 1.0},
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
                "retrieval_cases": [],
                "chat_cases": [
                    {
                        "id": "chat-missing",
                        "message": "Far unrelated evidence",
                        "retrieval_limit": 1,
                        "expected_evidence_ids": ["alpha"],
                        "expected_tool_queries": ["Far unrelated evidence"],
                    }
                ],
            },
        )
    )
    provider = MappingEmbeddingProvider(
        {
            "Alpha original evidence": _vector(0.9),
            "Far unrelated evidence": _vector(0.0),
        }
    )
    session = _make_session()

    report = run_chat_eval_suite(session, suite, provider=provider)

    assert report.status == "failed"
    assert report.metrics["chat_citation_coverage"] == 0.0
    assert report.cases[0].status == "failed"
    assert report.cases[0].metrics["citation_coverage"] == 0.0
    assert report.cases[0].observed_evidence_ids == ("far",)
    assert report.cases[0].errors == ("missing expected evidence: alpha",)


def test_run_chat_eval_suite_reports_tool_query_mismatch(
    tmp_path: Path,
) -> None:
    suite = load_eval_suite(
        _write_suite(
            tmp_path,
            {
                "schema_version": 1,
                "suite_id": "chat-tool-mismatch",
                "thresholds": {"chat_citation_coverage": 1.0},
                "evidence": [
                    {
                        "id": "alpha",
                        "text": "Alpha original evidence",
                        "source_type": "markdown",
                        "source_external_id": "alpha.md",
                    }
                ],
                "retrieval_cases": [],
                "chat_cases": [
                    {
                        "id": "chat-mismatch",
                        "message": "Alpha original evidence",
                        "retrieval_limit": 1,
                        "expected_evidence_ids": ["alpha"],
                        "expected_tool_queries": ["alpha evidence"],
                    }
                ],
            },
        )
    )
    provider = MappingEmbeddingProvider({"Alpha original evidence": _vector(0.0)})
    session = _make_session()

    report = run_chat_eval_suite(session, suite, provider=provider)

    assert report.status == "failed"
    assert report.metrics["chat_citation_coverage"] == 1.0
    assert report.cases[0].metrics["tool_query_match"] == 0.0
    assert report.cases[0].observed_tool_queries == ("Alpha original evidence",)
    assert report.cases[0].errors == (
        "tool query mismatch: expected ['alpha evidence'], "
        "got ['Alpha original evidence']",
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _vector(first: float) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = first
    return values
