"""Tests del contrato de fixtures de evals M6."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adaptive_rag.evals import (
    EvalCaseResult,
    EvalDatasetError,
    EvalRunReport,
    load_eval_suite,
    serialize_eval_report,
)
from adaptive_rag.retrieval import RetrievalMetadataFilter


def test_load_eval_suite_parses_versioned_retrieval_and_chat_cases(
    tmp_path: Path,
) -> None:
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "smoke",
            "description": "Small deterministic eval suite.",
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
                    "tags": ["docs", "v1"],
                    "metadata": {"title": "Alpha"},
                    "embedding": [0.0, 0.1],
                }
            ],
            "retrieval_cases": [
                {
                    "id": "retrieve-alpha",
                    "query": "What supports alpha?",
                    "limit": 2,
                    "case_metadata": {
                        "intent": "exact_match",
                        "difficulty": "easy",
                        "coverage_notes": ["baseline smoke"],
                    },
                    "metadata_filter": {
                        "source_type": "markdown",
                        "tags": ["docs", "v1"],
                    },
                    "expected_evidence_ids": ["alpha"],
                }
            ],
            "chat_cases": [
                {
                    "id": "chat-alpha",
                    "message": "Answer with alpha evidence.",
                    "retrieval_limit": 2,
                    "metadata_filter": {
                        "source_type": "markdown",
                        "tags": ["docs"],
                    },
                    "expected_evidence_ids": ["alpha"],
                    "expected_tool_queries": ["alpha evidence"],
                }
            ],
        },
    )

    suite = load_eval_suite(suite_path)

    assert suite.schema_version == 1
    assert suite.suite_id == "smoke"
    assert suite.description == "Small deterministic eval suite."
    assert suite.thresholds.retrieval_hit_rate == 1.0
    assert suite.thresholds.chat_citation_coverage == 1.0
    assert len(suite.evidence) == 1
    evidence = suite.evidence[0]
    assert evidence.id == "alpha"
    assert evidence.text == "Alpha original evidence"
    assert evidence.source_type == "markdown"
    assert evidence.source_external_id == "alpha.md"
    assert evidence.tags == ("docs", "v1")
    assert evidence.metadata == {"title": "Alpha"}
    assert evidence.embedding == (0.0, 0.1)
    retrieval_case = suite.retrieval_cases[0]
    assert retrieval_case.id == "retrieve-alpha"
    assert retrieval_case.query == "What supports alpha?"
    assert retrieval_case.limit == 2
    assert retrieval_case.case_metadata is not None
    assert retrieval_case.case_metadata.intent == "exact_match"
    assert retrieval_case.case_metadata.difficulty == "easy"
    assert retrieval_case.case_metadata.coverage_notes == ("baseline smoke",)
    assert retrieval_case.metadata_filter == RetrievalMetadataFilter(
        source_type="markdown",
        tags=("docs", "v1"),
    )
    assert retrieval_case.expected_evidence_ids == ("alpha",)
    chat_case = suite.chat_cases[0]
    assert chat_case.id == "chat-alpha"
    assert chat_case.message == "Answer with alpha evidence."
    assert chat_case.retrieval_limit == 2
    assert chat_case.metadata_filter == RetrievalMetadataFilter(
        source_type="markdown",
        tags=("docs",),
    )
    assert chat_case.expected_evidence_ids == ("alpha",)
    assert chat_case.expected_tool_queries == ("alpha evidence",)


def test_load_eval_suite_rejects_unknown_expected_evidence(
    tmp_path: Path,
) -> None:
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "broken",
            "thresholds": {},
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
                    "id": "retrieve-missing",
                    "query": "What supports beta?",
                    "expected_evidence_ids": ["beta"],
                }
            ],
            "chat_cases": [],
        },
    )

    with pytest.raises(
        EvalDatasetError,
        match="retrieve-missing references unknown evidence: beta",
    ):
        load_eval_suite(suite_path)


def test_load_eval_suite_rejects_unknown_fields_before_services(
    tmp_path: Path,
) -> None:
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "broken",
            "thresholds": {},
            "evidence": [],
            "retrieval_cases": [],
            "chat_cases": [],
            "unexpected": "value",
        },
    )

    with pytest.raises(EvalDatasetError, match="suite has unknown fields: unexpected"):
        load_eval_suite(suite_path)


def test_load_eval_suite_rejects_unknown_case_metadata_fields(
    tmp_path: Path,
) -> None:
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "broken",
            "thresholds": {},
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
                    "query": "What supports alpha?",
                    "case_metadata": {
                        "intent": "exact_match",
                        "unsupported": "value",
                    },
                    "expected_evidence_ids": ["alpha"],
                }
            ],
            "chat_cases": [],
        },
    )

    with pytest.raises(
        EvalDatasetError,
        match=r"retrieval_cases\[0\]\.case_metadata has unknown fields: unsupported",
    ):
        load_eval_suite(suite_path)


def test_load_eval_suite_rejects_missing_required_case_field(
    tmp_path: Path,
) -> None:
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "broken",
            "thresholds": {},
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
                    "expected_evidence_ids": ["alpha"],
                }
            ],
            "chat_cases": [],
        },
    )

    with pytest.raises(
        EvalDatasetError,
        match=r"retrieval_cases\[0\]\.query is required",
    ):
        load_eval_suite(suite_path)


def test_load_eval_suite_rejects_duplicate_evidence_ids(tmp_path: Path) -> None:
    suite_path = _write_suite(
        tmp_path,
        {
            "schema_version": 1,
            "suite_id": "broken",
            "thresholds": {},
            "evidence": [
                {
                    "id": "alpha",
                    "text": "Alpha original evidence",
                    "source_type": "markdown",
                    "source_external_id": "alpha.md",
                },
                {
                    "id": "alpha",
                    "text": "Duplicate alpha evidence",
                    "source_type": "markdown",
                    "source_external_id": "alpha-copy.md",
                },
            ],
            "retrieval_cases": [],
            "chat_cases": [],
        },
    )

    with pytest.raises(EvalDatasetError, match="evidence has duplicate id: alpha"):
        load_eval_suite(suite_path)


def test_load_eval_suite_parses_repo_retrieval_dataset_pack() -> None:
    suite = load_eval_suite(
        _repo_root() / "evals" / "fixtures" / "retrieval-dataset-pack.json"
    )

    assert suite.suite_id == "retrieval-dataset-pack"
    assert suite.description == "Representative offline retrieval eval dataset pack."
    assert suite.thresholds.retrieval_hit_rate == 1.0
    assert len(suite.evidence) == 10
    assert tuple(case.id for case in suite.retrieval_cases) == (
        "exact-api-error-fields",
        "paraphrase-invoice-export",
        "distractor-alpha-release-notes",
        "metadata-filter-docs-only",
        "multi-evidence-quality-gate",
        "rerank-helpful-candidate",
        "rerank-stable-exact",
    )
    assert suite.chat_cases == ()

    metadata_by_case = {
        case.id: case.case_metadata for case in suite.retrieval_cases
    }
    assert {
        case_id: metadata.intent if metadata is not None else None
        for case_id, metadata in metadata_by_case.items()
    } == {
        "exact-api-error-fields": "exact_match",
        "paraphrase-invoice-export": "paraphrase",
        "distractor-alpha-release-notes": "distractor",
        "metadata-filter-docs-only": "metadata_filter",
        "multi-evidence-quality-gate": "multi_evidence",
        "rerank-helpful-candidate": "rerank_helpful",
        "rerank-stable-exact": "rerank_stable",
    }
    assert metadata_by_case["multi-evidence-quality-gate"] is not None
    assert metadata_by_case[
        "multi-evidence-quality-gate"
    ].coverage_notes == (
        "requires both latency and cost evidence before changing retrieval",
    )

    filtered_case = next(
        case
        for case in suite.retrieval_cases
        if case.id == "metadata-filter-docs-only"
    )
    assert filtered_case.metadata_filter == RetrievalMetadataFilter(
        source_type="markdown",
        tags=("docs", "metadata"),
    )
    assert filtered_case.expected_evidence_ids == ("metadata-docs",)

    multi_case = next(
        case
        for case in suite.retrieval_cases
        if case.id == "multi-evidence-quality-gate"
    )
    assert multi_case.expected_evidence_ids == ("latency-metric", "cost-metric")


def test_serialize_eval_report_outputs_stable_json_payload() -> None:
    report = EvalRunReport(
        suite_id="smoke",
        status="passed",
        metrics={"chat_citation_coverage": 1.0, "retrieval_hit_rate": 1.0},
        thresholds={"chat_citation_coverage": 1.0, "retrieval_hit_rate": 1.0},
        cases=(
            EvalCaseResult(
                id="retrieve-alpha",
                kind="retrieval",
                status="passed",
                metrics={"hit": 1.0, "rank": 1.0},
            ),
            EvalCaseResult(
                id="chat-alpha",
                kind="chat",
                status="failed",
                metrics={"citation_coverage": 0.0},
                errors=("missing expected evidence alpha",),
            ),
        ),
    )

    assert serialize_eval_report(report) == {
        "suite_id": "smoke",
        "status": "passed",
        "metrics": {
            "chat_citation_coverage": 1.0,
            "retrieval_hit_rate": 1.0,
        },
        "thresholds": {
            "chat_citation_coverage": 1.0,
            "retrieval_hit_rate": 1.0,
        },
        "cases": [
            {
                "id": "retrieve-alpha",
                "kind": "retrieval",
                "status": "passed",
                "metrics": {"hit": 1.0, "rank": 1.0},
                "errors": [],
            },
            {
                "id": "chat-alpha",
                "kind": "chat",
                "status": "failed",
                "metrics": {"citation_coverage": 0.0},
                "errors": ["missing expected evidence alpha"],
            },
        ],
    }


def _write_suite(tmp_path: Path, payload: object) -> Path:
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(json.dumps(payload), encoding="utf-8")
    return suite_path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
