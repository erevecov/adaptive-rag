"""Serializacion estable de reportes de evals."""

from __future__ import annotations

from typing import Any

from adaptive_rag.evals.models import (
    EvalCaseResult,
    EvalObservedCitation,
    EvalRunReport,
)


def serialize_eval_report(report: EvalRunReport) -> dict[str, Any]:
    return {
        "suite_id": report.suite_id,
        "status": report.status,
        "metrics": _sorted_metrics(report.metrics),
        "thresholds": _sorted_metrics(report.thresholds),
        "cases": [serialize_eval_case_result(case) for case in report.cases],
    }


def serialize_eval_case_result(result: EvalCaseResult) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": result.id,
        "kind": result.kind,
        "status": result.status,
        "metrics": _sorted_metrics(result.metrics),
        "errors": list(result.errors),
    }
    if result.observed_evidence_ids:
        payload["observed_evidence_ids"] = list(result.observed_evidence_ids)
    if result.observed_citations:
        payload["observed_citations"] = [
            serialize_eval_observed_citation(citation)
            for citation in result.observed_citations
        ]
    if result.observed_tool_queries:
        payload["observed_tool_queries"] = list(result.observed_tool_queries)
    return payload


def serialize_eval_observed_citation(
    citation: EvalObservedCitation,
) -> dict[str, Any]:
    return {
        "evidence_id": citation.evidence_id,
        "chunk_id": citation.chunk_id,
        "rank": citation.rank,
        "score": citation.score,
        "source_external_id": citation.source_external_id,
        "snippet": citation.snippet,
    }


def _sorted_metrics(metrics: dict[str, float]) -> dict[str, float]:
    return {key: metrics[key] for key in sorted(metrics)}
