"""Comparaciones reutilizables entre dense baseline y reranked retrieval."""

from __future__ import annotations

from adaptive_rag.evals.models import (
    EvalCaseComparison,
    EvalCaseComparisonOutcome,
    EvalCaseResult,
    EvalRunReport,
    EvalSuite,
)


def build_rerank_comparison_metrics(
    *,
    dense_report: EvalRunReport,
    reranked_report: EvalRunReport,
    comparison_cases: tuple[EvalCaseComparison, ...],
) -> dict[str, float]:
    """Agrega metricas comparables entre dense y reranked retrieval."""

    dense_hit_rate = dense_report.metrics["retrieval_hit_rate"]
    reranked_hit_rate = reranked_report.metrics["retrieval_hit_rate"]
    case_count = len(comparison_cases)
    best_rank_delta_total = sum(
        comparison.best_rank_delta for comparison in comparison_cases
    )
    return {
        "dense_retrieval_hit_rate": dense_hit_rate,
        "dense_retrieval_passed_count": dense_report.metrics[
            "retrieval_passed_count"
        ],
        "rerank_best_rank_delta_avg": (
            best_rank_delta_total / case_count if case_count else 0.0
        ),
        "rerank_case_improvement_count": float(
            _comparison_outcome_count(comparison_cases, "improvement")
        ),
        "rerank_case_regression_count": float(
            _comparison_outcome_count(comparison_cases, "regression")
        ),
        "rerank_case_tie_count": float(
            _comparison_outcome_count(comparison_cases, "tie")
        ),
        "rerank_retrieval_hit_rate_delta": reranked_hit_rate - dense_hit_rate,
        "reranked_retrieval_hit_rate": reranked_hit_rate,
        "reranked_retrieval_passed_count": reranked_report.metrics[
            "retrieval_passed_count"
        ],
    }


def build_rerank_case_comparisons(
    *,
    suite: EvalSuite,
    dense_report: EvalRunReport,
    reranked_report: EvalRunReport,
) -> tuple[EvalCaseComparison, ...]:
    """Compara cada caso de retrieval entre dense baseline y rerank."""

    dense_cases = _cases_by_id(dense_report)
    reranked_cases = _cases_by_id(reranked_report)
    comparisons: list[EvalCaseComparison] = []
    for retrieval_case in suite.retrieval_cases:
        dense_case = dense_cases[retrieval_case.id]
        reranked_case = reranked_cases[retrieval_case.id]
        dense_best_rank = dense_case.metrics["best_rank"]
        reranked_best_rank = reranked_case.metrics["best_rank"]
        dense_expected = _observed_expected_evidence(
            dense_case,
            expected_evidence_ids=retrieval_case.expected_evidence_ids,
        )
        reranked_expected = _observed_expected_evidence(
            reranked_case,
            expected_evidence_ids=retrieval_case.expected_evidence_ids,
        )
        comparisons.append(
            EvalCaseComparison(
                id=retrieval_case.id,
                outcome=_rerank_case_outcome(
                    dense_case=dense_case,
                    reranked_case=reranked_case,
                ),
                dense_status=dense_case.status,
                reranked_status=reranked_case.status,
                dense_best_rank=dense_best_rank,
                reranked_best_rank=reranked_best_rank,
                best_rank_delta=_best_rank_delta(
                    dense_best_rank=dense_best_rank,
                    reranked_best_rank=reranked_best_rank,
                ),
                dense_observed_evidence_ids=dense_case.observed_evidence_ids,
                reranked_observed_evidence_ids=reranked_case.observed_evidence_ids,
                gained_evidence_ids=tuple(
                    evidence_id
                    for evidence_id in retrieval_case.expected_evidence_ids
                    if evidence_id in reranked_expected
                    and evidence_id not in dense_expected
                ),
                lost_evidence_ids=tuple(
                    evidence_id
                    for evidence_id in retrieval_case.expected_evidence_ids
                    if evidence_id in dense_expected
                    and evidence_id not in reranked_expected
                ),
            )
        )
    return tuple(comparisons)


def _cases_by_id(report: EvalRunReport) -> dict[str, EvalCaseResult]:
    return {case.id: case for case in report.cases}


def _observed_expected_evidence(
    case: EvalCaseResult,
    *,
    expected_evidence_ids: tuple[str, ...],
) -> set[str]:
    return set(case.observed_evidence_ids) & set(expected_evidence_ids)


def _rerank_case_outcome(
    *,
    dense_case: EvalCaseResult,
    reranked_case: EvalCaseResult,
) -> EvalCaseComparisonOutcome:
    dense_matched = dense_case.metrics["matched_count"]
    reranked_matched = reranked_case.metrics["matched_count"]
    if reranked_matched > dense_matched:
        return "improvement"
    if reranked_matched < dense_matched:
        return "regression"

    dense_best_rank = dense_case.metrics["best_rank"]
    reranked_best_rank = reranked_case.metrics["best_rank"]
    if reranked_best_rank > 0 and (
        dense_best_rank == 0 or reranked_best_rank < dense_best_rank
    ):
        return "improvement"
    if dense_best_rank > 0 and (
        reranked_best_rank == 0 or reranked_best_rank > dense_best_rank
    ):
        return "regression"
    return "tie"


def _best_rank_delta(
    *,
    dense_best_rank: float,
    reranked_best_rank: float,
) -> float:
    if dense_best_rank == 0 and reranked_best_rank == 0:
        return 0.0
    if dense_best_rank == 0:
        return reranked_best_rank
    if reranked_best_rank == 0:
        return -dense_best_rank
    return dense_best_rank - reranked_best_rank


def _comparison_outcome_count(
    comparison_cases: tuple[EvalCaseComparison, ...],
    outcome: EvalCaseComparisonOutcome,
) -> int:
    return sum(1 for comparison in comparison_cases if comparison.outcome == outcome)
