"""Quality gate M18 para comparar dense baseline vs retrieval graph opt-in."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.db.repositories import GraphProjectionRepository
from adaptive_rag.embeddings import DenseEmbeddingProvider, FakeDenseEmbeddingProvider
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
from adaptive_rag.evals.reports import serialize_eval_report
from adaptive_rag.evals.retrieval_runner import run_retrieval_eval_suite
from adaptive_rag.graph import GraphRetrievalResult, GraphRetriever

GraphQualityGateDecision = Literal["hold_default"]
GraphRetrieverFactory = Callable[[EvalRetrievalFixtureProject], GraphRetriever]

_OUTCOME_ORDER: tuple[EvalCaseComparisonOutcome, ...] = (
    "regression",
    "improvement",
    "tie",
)


@dataclass(frozen=True, slots=True)
class GraphQualityGateReport:
    """Reporte del gate M18 dense vs graph-enabled retrieval."""

    suite_id: str
    status: EvalStatus
    decision: GraphQualityGateDecision
    dense_baseline: EvalRunReport
    graph: EvalRunReport
    comparison_metrics: dict[str, float]
    comparison_cases: tuple[EvalCaseComparison, ...]


def run_graph_quality_gate_eval_suite(
    session: Session,
    suite: EvalSuite,
    *,
    provider: DenseEmbeddingProvider | None = None,
    graph_retriever_factory: GraphRetrieverFactory | None = None,
) -> GraphQualityGateReport:
    """Ejecuta la comparacion versionada dense vs graph sin Neo4j live."""

    active_provider = provider or FakeDenseEmbeddingProvider()
    fixture_project = build_retrieval_fixture_project(
        session,
        suite,
        provider=active_provider,
    )
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
    dense_report = run_retrieval_eval_suite(
        session,
        suite,
        provider=active_provider,
        fixture_project=fixture_project,
    )
    graph_report = run_retrieval_eval_suite(
        session,
        suite,
        provider=active_provider,
        strategy="graph",
        graph_retriever=graph_retriever,
        fixture_project=fixture_project,
    )
    comparison_cases = _build_graph_case_comparisons(
        suite=suite,
        dense_report=dense_report,
        graph_report=graph_report,
    )
    comparison_metrics = _build_graph_comparison_metrics(
        suite=suite,
        dense_report=dense_report,
        graph_report=graph_report,
        comparison_cases=comparison_cases,
    )
    status: EvalStatus = (
        "passed"
        if graph_report.status == "passed"
        and comparison_metrics["graph_case_regression_count"] == 0.0
        and comparison_metrics["graph_citation_coverage"] == 1.0
        and (
            comparison_metrics["graph_metadata_filter_case_count"]
            == comparison_metrics["graph_metadata_filter_passed_count"]
        )
        else "failed"
    )
    return GraphQualityGateReport(
        suite_id=suite.suite_id,
        status=status,
        decision="hold_default",
        dense_baseline=replace(dense_report, mode="offline"),
        graph=replace(graph_report, mode="offline"),
        comparison_metrics=comparison_metrics,
        comparison_cases=_order_gap_cases(comparison_cases),
    )


def serialize_graph_quality_gate_report(
    report: GraphQualityGateReport,
) -> dict[str, object]:
    """Serializa el gate graph con nombres especificos de graph."""

    return {
        "suite_id": report.suite_id,
        "status": report.status,
        "decision": report.decision,
        "dense_baseline": serialize_eval_report(report.dense_baseline),
        "graph": serialize_eval_report(report.graph),
        "comparison_metrics": _sorted_metrics(report.comparison_metrics),
        "comparison_cases": [
            _serialize_graph_case_comparison(comparison)
            for comparison in report.comparison_cases
        ],
    }


class FixtureOrderGraphRetriever:
    """Graph retriever determinista para evals offline sin servicio live."""

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


def _build_graph_comparison_metrics(
    *,
    suite: EvalSuite,
    dense_report: EvalRunReport,
    graph_report: EvalRunReport,
    comparison_cases: tuple[EvalCaseComparison, ...],
) -> dict[str, float]:
    dense_hit_rate = dense_report.metrics["retrieval_hit_rate"]
    graph_hit_rate = graph_report.metrics["retrieval_hit_rate"]
    case_count = len(comparison_cases)
    best_rank_delta_total = sum(
        comparison.best_rank_delta for comparison in comparison_cases
    )
    metadata_filter_case_count = sum(
        1 for case in suite.retrieval_cases if case.metadata_filter is not None
    )
    metadata_filter_passed = sum(
        1
        for retrieval_case, graph_case in zip(
            suite.retrieval_cases,
            graph_report.cases,
            strict=True,
        )
        if retrieval_case.metadata_filter is not None and graph_case.status == "passed"
    )
    return {
        "dense_retrieval_hit_rate": dense_hit_rate,
        "dense_retrieval_passed_count": dense_report.metrics[
            "retrieval_passed_count"
        ],
        "graph_best_rank_delta_avg": (
            best_rank_delta_total / case_count if case_count else 0.0
        ),
        "graph_case_improvement_count": float(
            _comparison_outcome_count(comparison_cases, "improvement")
        ),
        "graph_case_regression_count": float(
            _comparison_outcome_count(comparison_cases, "regression")
        ),
        "graph_case_tie_count": float(
            _comparison_outcome_count(comparison_cases, "tie")
        ),
        "graph_citation_coverage": _citation_coverage(graph_report),
        "graph_metadata_filter_case_count": float(metadata_filter_case_count),
        "graph_metadata_filter_passed_count": float(metadata_filter_passed),
        "graph_provider_cost_delta_usd": 0.0,
        "graph_retrieval_hit_rate": graph_hit_rate,
        "graph_retrieval_hit_rate_delta": graph_hit_rate - dense_hit_rate,
        "graph_retrieval_passed_count": graph_report.metrics[
            "retrieval_passed_count"
        ],
    }


def _build_graph_case_comparisons(
    *,
    suite: EvalSuite,
    dense_report: EvalRunReport,
    graph_report: EvalRunReport,
) -> tuple[EvalCaseComparison, ...]:
    dense_cases = _cases_by_id(dense_report)
    graph_cases = _cases_by_id(graph_report)
    comparisons: list[EvalCaseComparison] = []
    for retrieval_case in suite.retrieval_cases:
        dense_case = dense_cases[retrieval_case.id]
        graph_case = graph_cases[retrieval_case.id]
        dense_expected = _observed_expected_evidence(
            dense_case,
            expected_evidence_ids=retrieval_case.expected_evidence_ids,
        )
        graph_expected = _observed_expected_evidence(
            graph_case,
            expected_evidence_ids=retrieval_case.expected_evidence_ids,
        )
        comparisons.append(
            EvalCaseComparison(
                id=retrieval_case.id,
                outcome=_case_outcome(
                    dense_case=dense_case,
                    graph_case=graph_case,
                ),
                dense_status=dense_case.status,
                reranked_status=graph_case.status,
                dense_best_rank=dense_case.metrics["best_rank"],
                reranked_best_rank=graph_case.metrics["best_rank"],
                best_rank_delta=_best_rank_delta(
                    dense_best_rank=dense_case.metrics["best_rank"],
                    graph_best_rank=graph_case.metrics["best_rank"],
                ),
                dense_observed_evidence_ids=dense_case.observed_evidence_ids,
                reranked_observed_evidence_ids=graph_case.observed_evidence_ids,
                gained_evidence_ids=tuple(
                    evidence_id
                    for evidence_id in retrieval_case.expected_evidence_ids
                    if evidence_id in graph_expected
                    and evidence_id not in dense_expected
                ),
                lost_evidence_ids=tuple(
                    evidence_id
                    for evidence_id in retrieval_case.expected_evidence_ids
                    if evidence_id in dense_expected
                    and evidence_id not in graph_expected
                ),
            )
        )
    return tuple(comparisons)


def _serialize_graph_case_comparison(
    comparison: EvalCaseComparison,
) -> dict[str, object]:
    return {
        "id": comparison.id,
        "outcome": comparison.outcome,
        "dense_status": comparison.dense_status,
        "graph_status": comparison.reranked_status,
        "dense_best_rank": comparison.dense_best_rank,
        "graph_best_rank": comparison.reranked_best_rank,
        "best_rank_delta": comparison.best_rank_delta,
        "dense_observed_evidence_ids": list(comparison.dense_observed_evidence_ids),
        "graph_observed_evidence_ids": list(comparison.reranked_observed_evidence_ids),
        "gained_evidence_ids": list(comparison.gained_evidence_ids),
        "lost_evidence_ids": list(comparison.lost_evidence_ids),
    }


def _cases_by_id(report: EvalRunReport) -> dict[str, EvalCaseResult]:
    return {case.id: case for case in report.cases}


def _observed_expected_evidence(
    case: EvalCaseResult,
    *,
    expected_evidence_ids: tuple[str, ...],
) -> set[str]:
    return set(case.observed_evidence_ids) & set(expected_evidence_ids)


def _case_outcome(
    *,
    dense_case: EvalCaseResult,
    graph_case: EvalCaseResult,
) -> EvalCaseComparisonOutcome:
    dense_matched = dense_case.metrics["matched_count"]
    graph_matched = graph_case.metrics["matched_count"]
    if graph_matched > dense_matched:
        return "improvement"
    if graph_matched < dense_matched:
        return "regression"

    dense_best_rank = dense_case.metrics["best_rank"]
    graph_best_rank = graph_case.metrics["best_rank"]
    if graph_best_rank > 0 and (
        dense_best_rank == 0 or graph_best_rank < dense_best_rank
    ):
        return "improvement"
    if dense_best_rank > 0 and (
        graph_best_rank == 0 or graph_best_rank > dense_best_rank
    ):
        return "regression"
    return "tie"


def _best_rank_delta(
    *,
    dense_best_rank: float,
    graph_best_rank: float,
) -> float:
    if dense_best_rank == 0 and graph_best_rank == 0:
        return 0.0
    if dense_best_rank == 0:
        return graph_best_rank
    if graph_best_rank == 0:
        return -dense_best_rank
    return dense_best_rank - graph_best_rank


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


def _sorted_metrics(metrics: dict[str, float]) -> dict[str, float]:
    return {key: metrics[key] for key in sorted(metrics)}
