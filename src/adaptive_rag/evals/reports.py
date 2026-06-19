"""Serializacion estable de reportes de evals."""

from __future__ import annotations

from typing import Any

from adaptive_rag.evals.models import EvalCaseResult, EvalRunReport


def serialize_eval_report(report: EvalRunReport) -> dict[str, Any]:
    return {
        "suite_id": report.suite_id,
        "status": report.status,
        "metrics": _sorted_metrics(report.metrics),
        "thresholds": _sorted_metrics(report.thresholds),
        "cases": [serialize_eval_case_result(case) for case in report.cases],
    }


def serialize_eval_case_result(result: EvalCaseResult) -> dict[str, Any]:
    return {
        "id": result.id,
        "kind": result.kind,
        "status": result.status,
        "metrics": _sorted_metrics(result.metrics),
        "errors": list(result.errors),
    }


def _sorted_metrics(metrics: dict[str, float]) -> dict[str, float]:
    return {key: metrics[key] for key in sorted(metrics)}
