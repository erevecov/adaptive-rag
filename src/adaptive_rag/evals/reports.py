"""Serializacion estable de reportes de evals."""

from __future__ import annotations

from typing import Any

from adaptive_rag.evals.models import (
    EvalCaseResult,
    EvalObservedCitation,
    EvalProviderUsageOperationSummary,
    EvalProviderUsageSummary,
    EvalRunReport,
)


def serialize_eval_report(report: EvalRunReport) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "suite_id": report.suite_id,
        "status": report.status,
        "metrics": _sorted_metrics(report.metrics),
        "thresholds": _sorted_metrics(report.thresholds),
        "cases": [serialize_eval_case_result(case) for case in report.cases],
    }
    if report.mode == "hosted":
        payload["mode"] = report.mode
    if report.comparison_metrics:
        payload["comparison_metrics"] = _sorted_metrics(report.comparison_metrics)
    if report.provider_usage is not None:
        payload["provider_usage"] = serialize_eval_provider_usage(
            report.provider_usage
        )
    return payload


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


def serialize_eval_provider_usage(
    usage: EvalProviderUsageSummary,
) -> dict[str, Any]:
    return {
        "total_call_count": usage.total_call_count,
        "total_estimated_cost_usd": usage.total_estimated_cost_usd,
        "operations": [
            serialize_eval_provider_usage_operation(operation)
            for operation in usage.operations
        ],
    }


def serialize_eval_provider_usage_operation(
    operation: EvalProviderUsageOperationSummary,
) -> dict[str, Any]:
    return {
        "operation": operation.operation,
        "provider": operation.provider,
        "model": operation.model,
        "call_count": operation.call_count,
        "succeeded_count": operation.succeeded_count,
        "failed_count": operation.failed_count,
        "blocked_count": operation.blocked_count,
        "input_tokens": operation.input_tokens,
        "output_tokens": operation.output_tokens,
        "total_tokens": operation.total_tokens,
        "input_count": operation.input_count,
        "estimated_cost_usd": operation.estimated_cost_usd,
        "usage_unavailable_count": operation.usage_unavailable_count,
    }


def _sorted_metrics(metrics: dict[str, float]) -> dict[str, float]:
    return {key: metrics[key] for key in sorted(metrics)}
