"""Runner A/B para comparar varios candidate limits de rerank."""

from __future__ import annotations

from dataclasses import dataclass, replace

from sqlalchemy.orm import Session

from adaptive_rag.embeddings import DenseEmbeddingProvider
from adaptive_rag.evals.candidate_limit_matrix import (
    CandidateLimitEvalMatrix,
    build_candidate_limit_eval_matrix,
    serialize_candidate_limit_eval_matrix,
)
from adaptive_rag.evals.errors import EvalConfigurationError
from adaptive_rag.evals.fixtures import (
    EvalRetrievalFixtureProject,
    build_retrieval_fixture_project,
)
from adaptive_rag.evals.hosted import (
    summarize_provider_usage,
    validate_hosted_eval_options,
)
from adaptive_rag.evals.models import (
    EvalCaseComparison,
    EvalCaseComparisonOutcome,
    EvalProviderUsageSummary,
    EvalRunMode,
    EvalRunOptions,
    EvalRunReport,
    EvalStatus,
    EvalSuite,
)
from adaptive_rag.evals.reports import (
    serialize_eval_case_comparison,
    serialize_eval_provider_usage,
    serialize_eval_report,
)
from adaptive_rag.evals.retrieval_comparison import (
    build_rerank_case_comparisons,
    build_rerank_comparison_metrics,
)
from adaptive_rag.evals.retrieval_runner import run_retrieval_eval_suite
from adaptive_rag.provider_usage import InMemoryProviderUsageTracker
from adaptive_rag.rerank import RerankProvider
from adaptive_rag.retrieval import RetrievalRerankOptions

_OUTCOME_ORDER: tuple[EvalCaseComparisonOutcome, ...] = (
    "improvement",
    "regression",
    "tie",
)


@dataclass(frozen=True, slots=True)
class CandidateLimitABRunRow:
    """Fila A/B serializable para un candidate limit."""

    candidate_limit: int
    status: EvalStatus
    metrics: dict[str, float]
    comparison_metrics: dict[str, float]
    comparison_cases: tuple[EvalCaseComparison, ...]
    outcome_counts_by_intent: dict[str, dict[str, int]]
    outcome_counts_by_difficulty: dict[str, dict[str, int]]
    provider_usage: EvalProviderUsageSummary | None = None


@dataclass(frozen=True, slots=True)
class CandidateLimitABRunReport:
    """Reporte A/B completo para una suite y varios candidate limits."""

    suite_id: str
    mode: EvalRunMode
    matrix: CandidateLimitEvalMatrix
    dense_baseline: EvalRunReport
    rows: tuple[CandidateLimitABRunRow, ...]
    provider_usage: EvalProviderUsageSummary | None = None


def run_candidate_limit_ab_retrieval_eval_suite(
    session: Session,
    suite: EvalSuite,
    *,
    provider: DenseEmbeddingProvider,
    reranker: RerankProvider | None,
    candidate_limits: tuple[int, ...],
    usage_tracker: InMemoryProviderUsageTracker | None = None,
    options: EvalRunOptions | None = None,
) -> CandidateLimitABRunReport:
    """Ejecuta dense una vez y compara rerank para cada candidate limit."""

    active_options = options or EvalRunOptions()
    if reranker is None:
        raise EvalConfigurationError(
            "rerank provider is required for candidate_limit A/B runs"
        )
    if not candidate_limits:
        raise EvalConfigurationError("candidate_limits must not be empty")
    if active_options.is_hosted():
        validate_hosted_eval_options(active_options)
        if usage_tracker is None:
            raise EvalConfigurationError(
                "hosted candidate_limit A/B runs require usage_tracker"
            )

    matrix = build_candidate_limit_eval_matrix(
        suite,
        candidate_limits=candidate_limits,
    )
    fixture_project = build_retrieval_fixture_project(
        session,
        suite,
        provider=provider,
    )
    dense_report = run_retrieval_eval_suite(
        session,
        suite,
        provider=provider,
        fixture_project=fixture_project,
    )
    rows = tuple(
        _run_candidate_limit_row(
            session,
            suite,
            dense_report=dense_report,
            provider=provider,
            reranker=reranker,
            candidate_limit=row.candidate_limit,
            fixture_project=fixture_project,
            usage_tracker=usage_tracker if active_options.is_hosted() else None,
        )
        for row in matrix.rows
    )
    return CandidateLimitABRunReport(
        suite_id=suite.suite_id,
        mode=active_options.mode,
        matrix=matrix,
        dense_baseline=replace(dense_report, mode=active_options.mode),
        rows=rows,
        provider_usage=(
            summarize_provider_usage(usage_tracker.records)
            if active_options.is_hosted() and usage_tracker is not None
            else None
        ),
    )


def serialize_candidate_limit_ab_run_report(
    report: CandidateLimitABRunReport,
) -> dict[str, object]:
    """Serializa un reporte A/B con orden estable."""

    payload: dict[str, object] = {
        "suite_id": report.suite_id,
        "mode": report.mode,
        "matrix": serialize_candidate_limit_eval_matrix(report.matrix),
        "dense_baseline": serialize_eval_report(report.dense_baseline),
        "rows": [_serialize_row(row) for row in report.rows],
    }
    if report.provider_usage is not None:
        payload["provider_usage"] = serialize_eval_provider_usage(
            report.provider_usage
        )
    return payload


def _run_candidate_limit_row(
    session: Session,
    suite: EvalSuite,
    *,
    dense_report: EvalRunReport,
    provider: DenseEmbeddingProvider,
    reranker: RerankProvider,
    candidate_limit: int,
    fixture_project: EvalRetrievalFixtureProject,
    usage_tracker: InMemoryProviderUsageTracker | None,
) -> CandidateLimitABRunRow:
    usage_start = len(usage_tracker.records) if usage_tracker is not None else 0
    reranked_report = run_retrieval_eval_suite(
        session,
        suite,
        provider=provider,
        reranker=reranker,
        rerank_options=RetrievalRerankOptions(candidate_limit=candidate_limit),
        fixture_project=fixture_project,
    )
    comparison_cases = build_rerank_case_comparisons(
        suite=suite,
        dense_report=dense_report,
        reranked_report=reranked_report,
    )
    return CandidateLimitABRunRow(
        candidate_limit=candidate_limit,
        status=reranked_report.status,
        metrics=reranked_report.metrics,
        comparison_metrics=build_rerank_comparison_metrics(
            dense_report=dense_report,
            reranked_report=reranked_report,
            comparison_cases=comparison_cases,
        ),
        comparison_cases=comparison_cases,
        outcome_counts_by_intent=_outcome_counts_by_metadata(
            suite,
            comparison_cases,
            field="intent",
            fallback="unclassified",
        ),
        outcome_counts_by_difficulty=_outcome_counts_by_metadata(
            suite,
            comparison_cases,
            field="difficulty",
            fallback="unknown",
        ),
        provider_usage=(
            summarize_provider_usage(usage_tracker.records[usage_start:])
            if usage_tracker is not None
            else None
        ),
    )


def _outcome_counts_by_metadata(
    suite: EvalSuite,
    comparison_cases: tuple[EvalCaseComparison, ...],
    *,
    field: str,
    fallback: str,
) -> dict[str, dict[str, int]]:
    metadata_by_case_id = {
        case.id: case.case_metadata for case in suite.retrieval_cases
    }
    counts: dict[str, dict[str, int]] = {}
    for comparison in comparison_cases:
        metadata = metadata_by_case_id[comparison.id]
        value = getattr(metadata, field) if metadata is not None else None
        key = value or fallback
        bucket = counts.setdefault(key, _empty_outcome_counts())
        bucket[comparison.outcome] += 1
    return {
        key: {outcome: counts[key][outcome] for outcome in _OUTCOME_ORDER}
        for key in sorted(counts)
    }


def _empty_outcome_counts() -> dict[str, int]:
    return {outcome: 0 for outcome in _OUTCOME_ORDER}


def _serialize_row(row: CandidateLimitABRunRow) -> dict[str, object]:
    payload: dict[str, object] = {
        "candidate_limit": row.candidate_limit,
        "status": row.status,
        "metrics": _sorted_metrics(row.metrics),
        "comparison_metrics": _sorted_metrics(row.comparison_metrics),
        "outcome_counts_by_intent": _serialize_outcome_counts(
            row.outcome_counts_by_intent
        ),
        "outcome_counts_by_difficulty": _serialize_outcome_counts(
            row.outcome_counts_by_difficulty
        ),
        "comparison_cases": [
            serialize_eval_case_comparison(comparison)
            for comparison in row.comparison_cases
        ],
    }
    if row.provider_usage is not None:
        payload["provider_usage"] = serialize_eval_provider_usage(
            row.provider_usage
        )
    return payload


def _serialize_outcome_counts(
    counts: dict[str, dict[str, int]],
) -> dict[str, dict[str, int]]:
    return {
        key: {outcome: counts[key][outcome] for outcome in _OUTCOME_ORDER}
        for key in sorted(counts)
    }


def _sorted_metrics(metrics: dict[str, float]) -> dict[str, float]:
    return {key: metrics[key] for key in sorted(metrics)}
