"""M31 retrieval strategy gate across ready opt-in modes."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.db.repositories import GraphProjectionRepository
from adaptive_rag.embeddings import (
    DenseEmbeddingProvider,
    FakeDenseEmbeddingProvider,
    FakeSparseEmbeddingProvider,
    SparseEmbeddingProvider,
)
from adaptive_rag.evals.fixtures import (
    EvalRetrievalFixtureProject,
    build_retrieval_fixture_project,
)
from adaptive_rag.evals.metrics import ratio
from adaptive_rag.evals.models import (
    EvalCaseComparison,
    EvalCaseComparisonOutcome,
    EvalCaseResult,
    EvalRunReport,
    EvalStatus,
    EvalSuite,
)
from adaptive_rag.evals.reports import (
    serialize_eval_case_comparison,
    serialize_eval_report,
)
from adaptive_rag.evals.retrieval_runner import run_retrieval_eval_suite
from adaptive_rag.graph import GraphRetrievalResult, GraphRetriever
from adaptive_rag.rerank import FakeRerankProvider, RerankProvider
from adaptive_rag.retrieval import RetrievalRerankOptions, RetrievalStrategy

StrategyGateDecision = Literal[
    "promote",
    "keep_opt_in",
    "hold",
    "no_go",
    "needs_more_data",
]
StrategyGateRowStatus = Literal["passed", "failed", "skipped"]
StrategyGateStrategy = Literal[
    "dense",
    "contextual_dense",
    "lexical",
    "hybrid_rrf",
    "dense_sparse",
    "graph",
    "dense_rerank",
]
GraphRetrieverFactory = Callable[[EvalRetrievalFixtureProject], GraphRetriever]

DEFAULT_STRATEGIES: tuple[StrategyGateStrategy, ...] = (
    "dense",
    "contextual_dense",
    "lexical",
    "hybrid_rrf",
    "dense_sparse",
    "graph",
    "dense_rerank",
)
_OUTCOME_ORDER: tuple[EvalCaseComparisonOutcome, ...] = (
    "regression",
    "improvement",
    "tie",
)


@dataclass(frozen=True, slots=True)
class StrategyGateRow:
    """One strategy decision in the M31 comparison gate."""

    strategy: StrategyGateStrategy
    status: StrategyGateRowStatus
    decision: StrategyGateDecision
    reason: str
    metrics: dict[str, float]
    comparison_metrics: dict[str, float]
    comparison_cases: tuple[EvalCaseComparison, ...] = ()
    report: EvalRunReport | None = None


@dataclass(frozen=True, slots=True)
class StrategyGateReport:
    """Serializable M31 strategy gate report."""

    suite_id: str
    status: EvalStatus
    default_strategy: str
    recommended_default: str
    dense_baseline: EvalRunReport
    rows: tuple[StrategyGateRow, ...]


def run_retrieval_strategy_gate_eval_suite(
    session: Session,
    suite: EvalSuite,
    *,
    provider: DenseEmbeddingProvider | None = None,
    sparse_provider: SparseEmbeddingProvider | None = None,
    reranker: RerankProvider | None = None,
    rerank_candidate_limit: int | None = None,
    graph_retriever_factory: GraphRetrieverFactory | None = None,
    strategies: tuple[StrategyGateStrategy, ...] = DEFAULT_STRATEGIES,
) -> StrategyGateReport:
    """Compare ready retrieval modes and emit conservative promotion decisions."""

    active_provider = provider or FakeDenseEmbeddingProvider()
    active_sparse_provider = sparse_provider or FakeSparseEmbeddingProvider()
    active_reranker = reranker or FakeRerankProvider()
    fixture_project = build_retrieval_fixture_project(
        session,
        suite,
        provider=active_provider,
    )
    dense_report = run_retrieval_eval_suite(
        session,
        suite,
        provider=active_provider,
        fixture_project=fixture_project,
    )
    rows = tuple(
        _run_strategy_row(
            session,
            suite,
            strategy=strategy,
            dense_report=dense_report,
            provider=active_provider,
            sparse_provider=active_sparse_provider,
            reranker=active_reranker,
            rerank_candidate_limit=(
                rerank_candidate_limit or _default_rerank_candidate_limit(suite)
            ),
            fixture_project=fixture_project,
            graph_retriever_factory=graph_retriever_factory,
        )
        for strategy in strategies
    )
    recommended_default = _recommended_default(rows)
    status: EvalStatus = (
        "failed"
        if dense_report.status == "failed"
        or any(row.decision == "no_go" for row in rows)
        else "passed"
    )
    return StrategyGateReport(
        suite_id=suite.suite_id,
        status=status,
        default_strategy="dense",
        recommended_default=recommended_default,
        dense_baseline=replace(dense_report, mode="offline"),
        rows=rows,
    )


def serialize_retrieval_strategy_gate_report(
    report: StrategyGateReport,
) -> dict[str, object]:
    """Serialize strategy gate output with stable key ordering."""

    return {
        "suite_id": report.suite_id,
        "status": report.status,
        "default_strategy": report.default_strategy,
        "recommended_default": report.recommended_default,
        "dense_baseline": serialize_eval_report(report.dense_baseline),
        "strategy_decisions": [_serialize_row(row) for row in report.rows],
    }


def _run_strategy_row(
    session: Session,
    suite: EvalSuite,
    *,
    strategy: StrategyGateStrategy,
    dense_report: EvalRunReport,
    provider: DenseEmbeddingProvider,
    sparse_provider: SparseEmbeddingProvider,
    reranker: RerankProvider,
    rerank_candidate_limit: int,
    fixture_project: EvalRetrievalFixtureProject,
    graph_retriever_factory: GraphRetrieverFactory | None,
) -> StrategyGateRow:
    if strategy == "dense":
        return StrategyGateRow(
            strategy="dense",
            status=dense_report.status,
            decision="promote" if dense_report.status == "passed" else "no_go",
            reason=(
                "dense baseline passes and remains the recommended default"
                if dense_report.status == "passed"
                else "dense baseline failed the retrieval suite"
            ),
            metrics=dense_report.metrics,
            comparison_metrics={},
            report=replace(dense_report, mode="offline"),
        )
    if strategy == "contextual_dense" and not _suite_has_contextual_summaries(suite):
        return StrategyGateRow(
            strategy="contextual_dense",
            status="skipped",
            decision="needs_more_data",
            reason=(
                "contextual_dense requires eval evidence with contextual_summary "
                "values"
            ),
            metrics={},
            comparison_metrics={},
        )

    strategy_report = _run_strategy_report(
        session,
        suite,
        strategy=strategy,
        provider=provider,
        sparse_provider=sparse_provider,
        reranker=reranker,
        rerank_candidate_limit=rerank_candidate_limit,
        fixture_project=fixture_project,
        graph_retriever_factory=graph_retriever_factory,
    )
    comparison_cases = _order_gap_cases(
        _build_strategy_case_comparisons(
            suite=suite,
            dense_report=dense_report,
            strategy_report=strategy_report,
        )
    )
    comparison_metrics = _build_strategy_comparison_metrics(
        suite=suite,
        strategy=strategy,
        dense_report=dense_report,
        strategy_report=strategy_report,
        comparison_cases=comparison_cases,
    )
    decision, reason = _decide_strategy(
        strategy=strategy,
        strategy_report=strategy_report,
        comparison_metrics=comparison_metrics,
    )
    return StrategyGateRow(
        strategy=strategy,
        status=strategy_report.status,
        decision=decision,
        reason=reason,
        metrics=strategy_report.metrics,
        comparison_metrics=comparison_metrics,
        comparison_cases=comparison_cases,
        report=replace(strategy_report, mode="offline"),
    )


def _run_strategy_report(
    session: Session,
    suite: EvalSuite,
    *,
    strategy: StrategyGateStrategy,
    provider: DenseEmbeddingProvider,
    sparse_provider: SparseEmbeddingProvider,
    reranker: RerankProvider,
    rerank_candidate_limit: int,
    fixture_project: EvalRetrievalFixtureProject,
    graph_retriever_factory: GraphRetrieverFactory | None,
) -> EvalRunReport:
    if strategy == "contextual_dense":
        contextual_fixture = build_retrieval_fixture_project(
            session,
            suite,
            provider=provider,
            use_contextual_summaries=True,
        )
        return run_retrieval_eval_suite(
            session,
            suite,
            provider=provider,
            fixture_project=contextual_fixture,
        )
    if strategy == "dense_rerank":
        return run_retrieval_eval_suite(
            session,
            suite,
            provider=provider,
            reranker=reranker,
            rerank_options=RetrievalRerankOptions(
                candidate_limit=rerank_candidate_limit,
            ),
            fixture_project=fixture_project,
        )
    if strategy == "graph":
        GraphProjectionRepository(session).mark_ready(
            project_id=fixture_project.project_id,
            source_watermark=f"eval:{suite.suite_id}",
            indexed_at=datetime.now(UTC),
        )
        graph_retriever = (
            graph_retriever_factory(fixture_project)
            if graph_retriever_factory is not None
            else FixtureOrderGraphRetriever(fixture_project=fixture_project)
        )
        return run_retrieval_eval_suite(
            session,
            suite,
            provider=provider,
            strategy="graph",
            graph_retriever=graph_retriever,
            fixture_project=fixture_project,
        )
    retrieval_strategy = _to_retrieval_strategy(strategy)
    return run_retrieval_eval_suite(
        session,
        suite,
        provider=provider,
        sparse_provider=(
            sparse_provider if retrieval_strategy == "dense_sparse" else None
        ),
        strategy=retrieval_strategy,
        fixture_project=fixture_project,
    )


class FixtureOrderGraphRetriever:
    """Deterministic graph retriever for offline strategy gate runs."""

    def __init__(self, *, fixture_project: EvalRetrievalFixtureProject) -> None:
        ordered = tuple(fixture_project.evidence_id_by_chunk_id)
        self._rank_by_chunk_id = {
            chunk_id: rank for rank, chunk_id in enumerate(ordered)
        }

    def expand_project_chunks(
        self,
        *,
        project_id: UUID,
        seed_chunk_ids: Sequence[UUID],
        limit: int,
    ) -> tuple[GraphRetrievalResult, ...]:
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


def _to_retrieval_strategy(strategy: StrategyGateStrategy) -> RetrievalStrategy:
    if strategy not in ("dense", "lexical", "hybrid_rrf", "dense_sparse", "graph"):
        raise ValueError(f"{strategy} is not a RetrievalStrategy")
    return strategy


def _build_strategy_comparison_metrics(
    *,
    suite: EvalSuite,
    strategy: StrategyGateStrategy,
    dense_report: EvalRunReport,
    strategy_report: EvalRunReport,
    comparison_cases: tuple[EvalCaseComparison, ...],
) -> dict[str, float]:
    dense_hit_rate = dense_report.metrics["retrieval_hit_rate"]
    strategy_hit_rate = strategy_report.metrics["retrieval_hit_rate"]
    case_count = len(comparison_cases)
    best_rank_delta_total = sum(
        comparison.best_rank_delta for comparison in comparison_cases
    )
    metadata_filter_case_count = sum(
        1 for case in suite.retrieval_cases if case.metadata_filter is not None
    )
    metadata_filter_passed = sum(
        1
        for retrieval_case, strategy_case in zip(
            suite.retrieval_cases,
            strategy_report.cases,
            strict=True,
        )
        if retrieval_case.metadata_filter is not None
        and strategy_case.status == "passed"
    )
    prefix = strategy
    return {
        f"{prefix}_best_rank_delta_avg": (
            best_rank_delta_total / case_count if case_count else 0.0
        ),
        f"{prefix}_case_improvement_count": float(
            _comparison_outcome_count(comparison_cases, "improvement")
        ),
        f"{prefix}_case_regression_count": float(
            _comparison_outcome_count(comparison_cases, "regression")
        ),
        f"{prefix}_case_tie_count": float(
            _comparison_outcome_count(comparison_cases, "tie")
        ),
        f"{prefix}_citation_coverage": _citation_coverage(strategy_report),
        f"{prefix}_metadata_filter_case_count": float(metadata_filter_case_count),
        f"{prefix}_metadata_filter_passed_count": float(metadata_filter_passed),
        f"{prefix}_provider_cost_delta_usd": 0.0,
        f"{prefix}_retrieval_hit_rate": strategy_hit_rate,
        f"{prefix}_retrieval_hit_rate_delta": strategy_hit_rate - dense_hit_rate,
        f"{prefix}_retrieval_passed_count": strategy_report.metrics[
            "retrieval_passed_count"
        ],
    }


def _build_strategy_case_comparisons(
    *,
    suite: EvalSuite,
    dense_report: EvalRunReport,
    strategy_report: EvalRunReport,
) -> tuple[EvalCaseComparison, ...]:
    dense_cases = _cases_by_id(dense_report)
    strategy_cases = _cases_by_id(strategy_report)
    comparisons: list[EvalCaseComparison] = []
    for retrieval_case in suite.retrieval_cases:
        dense_case = dense_cases[retrieval_case.id]
        strategy_case = strategy_cases[retrieval_case.id]
        dense_expected = _observed_expected_evidence(
            dense_case,
            expected_evidence_ids=retrieval_case.expected_evidence_ids,
        )
        strategy_expected = _observed_expected_evidence(
            strategy_case,
            expected_evidence_ids=retrieval_case.expected_evidence_ids,
        )
        comparisons.append(
            EvalCaseComparison(
                id=retrieval_case.id,
                outcome=_case_outcome(
                    dense_case=dense_case,
                    strategy_case=strategy_case,
                ),
                dense_status=dense_case.status,
                reranked_status=strategy_case.status,
                dense_best_rank=dense_case.metrics["best_rank"],
                reranked_best_rank=strategy_case.metrics["best_rank"],
                best_rank_delta=_best_rank_delta(
                    dense_best_rank=dense_case.metrics["best_rank"],
                    strategy_best_rank=strategy_case.metrics["best_rank"],
                ),
                dense_observed_evidence_ids=dense_case.observed_evidence_ids,
                reranked_observed_evidence_ids=(
                    strategy_case.observed_evidence_ids
                ),
                gained_evidence_ids=tuple(
                    evidence_id
                    for evidence_id in retrieval_case.expected_evidence_ids
                    if evidence_id in strategy_expected
                    and evidence_id not in dense_expected
                ),
                lost_evidence_ids=tuple(
                    evidence_id
                    for evidence_id in retrieval_case.expected_evidence_ids
                    if evidence_id in dense_expected
                    and evidence_id not in strategy_expected
                ),
            )
        )
    return tuple(comparisons)


def _decide_strategy(
    *,
    strategy: StrategyGateStrategy,
    strategy_report: EvalRunReport,
    comparison_metrics: dict[str, float],
) -> tuple[StrategyGateDecision, str]:
    prefix = strategy
    if strategy_report.status == "failed":
        return "no_go", f"{strategy} fails the retrieval suite"
    if comparison_metrics[f"{prefix}_case_regression_count"] > 0.0:
        return "no_go", f"{strategy} introduces retrieval regressions"
    if comparison_metrics[f"{prefix}_citation_coverage"] < 1.0:
        return "no_go", f"{strategy} does not preserve citation coverage"
    if (
        comparison_metrics[f"{prefix}_metadata_filter_passed_count"]
        < comparison_metrics[f"{prefix}_metadata_filter_case_count"]
    ):
        return "no_go", f"{strategy} does not preserve metadata filter behavior"
    if strategy == "graph":
        return (
            "hold",
            (
                "graph passes the offline quality contract but still requires "
                "live operational evidence before promotion"
            ),
        )
    if comparison_metrics[f"{prefix}_retrieval_hit_rate_delta"] > 0.0:
        return "promote", f"{strategy} improves retrieval hit rate without regressions"
    return "keep_opt_in", f"{strategy} matches dense without regressions"


def _serialize_row(row: StrategyGateRow) -> dict[str, object]:
    payload: dict[str, object] = {
        "strategy": row.strategy,
        "status": row.status,
        "decision": row.decision,
        "reason": row.reason,
        "metrics": _sorted_metrics(row.metrics),
        "comparison_metrics": _sorted_metrics(row.comparison_metrics),
    }
    gap_cases = tuple(
        comparison
        for comparison in row.comparison_cases
        if comparison.outcome != "tie"
    )
    if gap_cases:
        payload["comparison_cases"] = [
            serialize_eval_case_comparison(comparison)
            for comparison in gap_cases
        ]
    return payload


def _cases_by_id(report: EvalRunReport) -> dict[str, EvalCaseResult]:
    return {case.id: case for case in report.cases}


def _case_outcome(
    *,
    dense_case: EvalCaseResult,
    strategy_case: EvalCaseResult,
) -> EvalCaseComparisonOutcome:
    dense_matched = dense_case.metrics["matched_count"]
    strategy_matched = strategy_case.metrics["matched_count"]
    if strategy_matched > dense_matched:
        return "improvement"
    if strategy_matched < dense_matched:
        return "regression"

    dense_best_rank = dense_case.metrics["best_rank"]
    strategy_best_rank = strategy_case.metrics["best_rank"]
    if strategy_best_rank > 0 and (
        dense_best_rank == 0 or strategy_best_rank < dense_best_rank
    ):
        return "improvement"
    if dense_best_rank > 0 and (
        strategy_best_rank == 0 or strategy_best_rank > dense_best_rank
    ):
        return "regression"
    return "tie"


def _best_rank_delta(
    *,
    dense_best_rank: float,
    strategy_best_rank: float,
) -> float:
    if dense_best_rank == 0 and strategy_best_rank == 0:
        return 0.0
    if dense_best_rank == 0:
        return strategy_best_rank
    if strategy_best_rank == 0:
        return -dense_best_rank
    return dense_best_rank - strategy_best_rank


def _observed_expected_evidence(
    case: EvalCaseResult,
    *,
    expected_evidence_ids: tuple[str, ...],
) -> set[str]:
    return set(case.observed_evidence_ids) & set(expected_evidence_ids)


def _comparison_outcome_count(
    comparison_cases: tuple[EvalCaseComparison, ...],
    outcome: EvalCaseComparisonOutcome,
) -> int:
    return sum(1 for comparison in comparison_cases if comparison.outcome == outcome)


def _citation_coverage(report: EvalRunReport) -> float:
    retrieved_count = sum(case.metrics["retrieved_count"] for case in report.cases)
    citation_count = sum(len(case.observed_citations) for case in report.cases)
    return ratio(citation_count, int(retrieved_count))


def _order_gap_cases(
    comparison_cases: tuple[EvalCaseComparison, ...],
) -> tuple[EvalCaseComparison, ...]:
    outcome_rank = {outcome: index for index, outcome in enumerate(_OUTCOME_ORDER)}
    return tuple(
        comparison
        for _, comparison in sorted(
            enumerate(comparison_cases),
            key=lambda item: (outcome_rank[item[1].outcome], item[0]),
        )
    )


def _suite_has_contextual_summaries(suite: EvalSuite) -> bool:
    return any(bool(evidence.contextual_summary) for evidence in suite.evidence)


def _default_rerank_candidate_limit(suite: EvalSuite) -> int:
    max_case_limit = max((case.limit for case in suite.retrieval_cases), default=1)
    return max_case_limit + 2


def _recommended_default(rows: tuple[StrategyGateRow, ...]) -> str:
    for row in rows:
        if row.strategy != "dense" and row.decision == "promote":
            return row.strategy
    return "dense"


def _sorted_metrics(metrics: dict[str, float]) -> dict[str, float]:
    return {key: metrics[key] for key in sorted(metrics)}
