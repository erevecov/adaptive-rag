from __future__ import annotations

from pathlib import Path

import pytest

from adaptive_rag.evals import EvalConfigurationError, load_eval_suite
from adaptive_rag.evals.candidate_limit_matrix import (
    build_candidate_limit_eval_matrix,
    serialize_candidate_limit_eval_matrix,
)


def test_build_candidate_limit_eval_matrix_groups_cases_by_metadata() -> None:
    suite = load_eval_suite(
        _repo_root() / "evals" / "fixtures" / "retrieval-dataset-pack.json"
    )

    matrix = build_candidate_limit_eval_matrix(
        suite,
        candidate_limits=(3, 5, 8),
    )

    assert matrix.suite_id == "retrieval-dataset-pack"
    assert matrix.max_case_limit == 3
    assert matrix.case_count == 7
    assert matrix.intent_counts == {
        "distractor": 1,
        "exact_match": 1,
        "metadata_filter": 1,
        "multi_evidence": 1,
        "paraphrase": 1,
        "rerank_helpful": 1,
        "rerank_stable": 1,
    }
    assert matrix.difficulty_counts == {
        "easy": 2,
        "hard": 1,
        "medium": 4,
    }
    assert [row.candidate_limit for row in matrix.rows] == [3, 5, 8]
    assert all(row.case_count == 7 for row in matrix.rows)
    assert matrix.rows[0].case_ids_by_intent["metadata_filter"] == (
        "metadata-filter-docs-only",
    )
    assert matrix.rows[0].case_ids_by_difficulty["hard"] == (
        "multi-evidence-quality-gate",
    )

    assert serialize_candidate_limit_eval_matrix(matrix) == {
        "suite_id": "retrieval-dataset-pack",
        "case_count": 7,
        "max_case_limit": 3,
        "intent_counts": {
            "distractor": 1,
            "exact_match": 1,
            "metadata_filter": 1,
            "multi_evidence": 1,
            "paraphrase": 1,
            "rerank_helpful": 1,
            "rerank_stable": 1,
        },
        "difficulty_counts": {
            "easy": 2,
            "hard": 1,
            "medium": 4,
        },
        "rows": [
            {
                "candidate_limit": 3,
                "case_count": 7,
                "case_ids_by_intent": {
                    "distractor": ["distractor-alpha-release-notes"],
                    "exact_match": ["exact-api-error-fields"],
                    "metadata_filter": ["metadata-filter-docs-only"],
                    "multi_evidence": ["multi-evidence-quality-gate"],
                    "paraphrase": ["paraphrase-invoice-export"],
                    "rerank_helpful": ["rerank-helpful-candidate"],
                    "rerank_stable": ["rerank-stable-exact"],
                },
                "case_ids_by_difficulty": {
                    "easy": ["exact-api-error-fields", "rerank-stable-exact"],
                    "hard": ["multi-evidence-quality-gate"],
                    "medium": [
                        "paraphrase-invoice-export",
                        "distractor-alpha-release-notes",
                        "metadata-filter-docs-only",
                        "rerank-helpful-candidate",
                    ],
                },
            },
            {
                "candidate_limit": 5,
                "case_count": 7,
                "case_ids_by_intent": {
                    "distractor": ["distractor-alpha-release-notes"],
                    "exact_match": ["exact-api-error-fields"],
                    "metadata_filter": ["metadata-filter-docs-only"],
                    "multi_evidence": ["multi-evidence-quality-gate"],
                    "paraphrase": ["paraphrase-invoice-export"],
                    "rerank_helpful": ["rerank-helpful-candidate"],
                    "rerank_stable": ["rerank-stable-exact"],
                },
                "case_ids_by_difficulty": {
                    "easy": ["exact-api-error-fields", "rerank-stable-exact"],
                    "hard": ["multi-evidence-quality-gate"],
                    "medium": [
                        "paraphrase-invoice-export",
                        "distractor-alpha-release-notes",
                        "metadata-filter-docs-only",
                        "rerank-helpful-candidate",
                    ],
                },
            },
            {
                "candidate_limit": 8,
                "case_count": 7,
                "case_ids_by_intent": {
                    "distractor": ["distractor-alpha-release-notes"],
                    "exact_match": ["exact-api-error-fields"],
                    "metadata_filter": ["metadata-filter-docs-only"],
                    "multi_evidence": ["multi-evidence-quality-gate"],
                    "paraphrase": ["paraphrase-invoice-export"],
                    "rerank_helpful": ["rerank-helpful-candidate"],
                    "rerank_stable": ["rerank-stable-exact"],
                },
                "case_ids_by_difficulty": {
                    "easy": ["exact-api-error-fields", "rerank-stable-exact"],
                    "hard": ["multi-evidence-quality-gate"],
                    "medium": [
                        "paraphrase-invoice-export",
                        "distractor-alpha-release-notes",
                        "metadata-filter-docs-only",
                        "rerank-helpful-candidate",
                    ],
                },
            },
        ],
    }


def test_build_candidate_limit_eval_matrix_rejects_invalid_limits() -> None:
    suite = load_eval_suite(
        _repo_root() / "evals" / "fixtures" / "retrieval-dataset-pack.json"
    )

    with pytest.raises(
        EvalConfigurationError,
        match="candidate_limit values must be unique",
    ):
        build_candidate_limit_eval_matrix(suite, candidate_limits=(3, 3))

    with pytest.raises(
        EvalConfigurationError,
        match="candidate_limit must be positive",
    ):
        build_candidate_limit_eval_matrix(suite, candidate_limits=(0,))

    with pytest.raises(
        EvalConfigurationError,
        match=(
            "candidate_limit must be greater than or equal to every "
            "retrieval case limit"
        ),
    ):
        build_candidate_limit_eval_matrix(suite, candidate_limits=(2,))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
