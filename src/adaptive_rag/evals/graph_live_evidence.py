"""M19 graph live evidence reporting."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast
from uuid import UUID

from adaptive_rag.evals.errors import EvalConfigurationError, EvalDatasetError
from adaptive_rag.evals.graph_quality_gate_runner import (
    GraphQualityGateDecision,
    GraphQualityGateReport,
    serialize_graph_quality_gate_report,
)
from adaptive_rag.evals.models import EvalStatus
from adaptive_rag.graph import (
    GraphBackfillOperationName,
    GraphBackfillOperationReport,
    GraphProjectionStatus,
    GraphRetrievalSmokeReport,
    GraphRetrievalSmokeStatus,
)


@dataclass(frozen=True, slots=True)
class GraphOperationalCost:
    """Costo operacional declarado para correr graph infra."""

    amount_usd: float | None = None
    currency: Literal["USD"] = "USD"
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class GraphLiveEvidenceReport:
    """Reporte M19 que combina calidad dense-vs-graph y evidencia live."""

    suite_id: str
    status: EvalStatus
    decision: GraphQualityGateDecision
    quality_report: GraphQualityGateReport
    operational_metrics: dict[str, float]
    error_codes: dict[str, int]
    graph_operational_cost: GraphOperationalCost
    operation_reports: tuple[GraphBackfillOperationReport, ...]
    retrieval_smoke_reports: tuple[GraphRetrievalSmokeReport, ...]


def build_graph_live_evidence_report(
    *,
    quality_report: GraphQualityGateReport,
    operation_reports: tuple[GraphBackfillOperationReport, ...] = (),
    retrieval_smoke_reports: tuple[GraphRetrievalSmokeReport, ...] = (),
    graph_operational_cost: GraphOperationalCost | None = None,
) -> GraphLiveEvidenceReport:
    """Build a reproducible live evidence report from prior graph artifacts."""

    active_cost = graph_operational_cost or GraphOperationalCost()
    if active_cost.amount_usd is not None and active_cost.amount_usd < 0:
        raise EvalConfigurationError("graph operational cost must not be negative")
    error_codes = _error_code_counts(operation_reports, retrieval_smoke_reports)
    operational_metrics = _operational_metrics(
        operation_reports=operation_reports,
        retrieval_smoke_reports=retrieval_smoke_reports,
        graph_operational_cost=active_cost,
        error_codes=error_codes,
    )
    return GraphLiveEvidenceReport(
        suite_id=quality_report.suite_id,
        status=_report_status(
            quality_report=quality_report,
            operation_reports=operation_reports,
            retrieval_smoke_reports=retrieval_smoke_reports,
        ),
        decision=quality_report.decision,
        quality_report=quality_report,
        operational_metrics=operational_metrics,
        error_codes=dict(sorted(error_codes.items())),
        graph_operational_cost=active_cost,
        operation_reports=operation_reports,
        retrieval_smoke_reports=retrieval_smoke_reports,
    )


def serialize_graph_live_evidence_report(
    report: GraphLiveEvidenceReport,
) -> dict[str, object]:
    """Serialize M19 evidence with quality and operational sections separated."""

    quality_payload = serialize_graph_quality_gate_report(report.quality_report)
    return {
        "suite_id": report.suite_id,
        "status": report.status,
        "decision": report.decision,
        "dense_baseline": quality_payload["dense_baseline"],
        "graph": quality_payload["graph"],
        "comparison_metrics": quality_payload["comparison_metrics"],
        "comparison_cases": quality_payload["comparison_cases"],
        "operational_metrics": _sorted_metrics(report.operational_metrics),
        "error_codes": dict(sorted(report.error_codes.items())),
        "graph_operational_cost": {
            "amount_usd": report.graph_operational_cost.amount_usd,
            "currency": report.graph_operational_cost.currency,
            "notes": report.graph_operational_cost.notes,
        },
        "operation_reports": [
            _serialize_operation_report(operation_report)
            for operation_report in report.operation_reports
        ],
        "retrieval_smoke_reports": [
            _serialize_retrieval_smoke_report(retrieval_report)
            for retrieval_report in report.retrieval_smoke_reports
        ],
    }


def load_graph_operation_report(path: Path) -> GraphBackfillOperationReport:
    """Load a JSON report emitted by `adaptive-rag graph backfill/reindex`."""

    data = _load_json_object(path)
    try:
        return GraphBackfillOperationReport(
            project_id=UUID(str(data["project_id"])),
            backend=cast(Literal["neo4j"], data["backend"]),
            operation=cast(GraphBackfillOperationName, data["operation"]),
            previous_status=str(data["previous_status"]),
            status=cast(GraphProjectionStatus, data["status"]),
            source_watermark=str(data["source_watermark"]),
            duration_ms=int(data["duration_ms"]),
            node_count=_optional_int(data.get("node_count")),
            relationship_count=_optional_int(data.get("relationship_count")),
            error_code=_optional_str(data.get("error_code")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise EvalDatasetError(
            f"could not parse graph operation report: {path}"
        ) from exc


def load_graph_retrieval_smoke_report(path: Path) -> GraphRetrievalSmokeReport:
    """Load a JSON report emitted by `adaptive-rag graph retrieval-smoke`."""

    data = _load_json_object(path)
    try:
        return GraphRetrievalSmokeReport(
            project_id=UUID(str(data["project_id"])),
            backend=cast(Literal["neo4j"], data["backend"]),
            status=cast(GraphRetrievalSmokeStatus, data["status"]),
            requested_strategy=cast(Literal["graph"], data["requested_strategy"]),
            result_count=int(data["result_count"]),
            graph_result_count=int(data["graph_result_count"]),
            citation_count=int(data["citation_count"]),
            fallback_reason=_optional_str(data.get("fallback_reason")),
            latency_ms=int(data["latency_ms"]),
            limit=int(data["limit"]),
            chunk_ids=tuple(UUID(str(chunk_id)) for chunk_id in data["chunk_ids"]),
            source_external_ids=tuple(
                str(source_external_id)
                for source_external_id in data["source_external_ids"]
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise EvalDatasetError(
            f"could not parse graph retrieval smoke report: {path}"
        ) from exc


def _operational_metrics(
    *,
    operation_reports: tuple[GraphBackfillOperationReport, ...],
    retrieval_smoke_reports: tuple[GraphRetrievalSmokeReport, ...],
    graph_operational_cost: GraphOperationalCost,
    error_codes: Counter[str],
) -> dict[str, float]:
    backfills = tuple(
        report for report in operation_reports if report.operation == "backfill"
    )
    reindexes = tuple(
        report for report in operation_reports if report.operation == "reindex"
    )
    smoke_count = len(retrieval_smoke_reports)
    fallback_count = sum(
        1 for report in retrieval_smoke_reports if report.status == "fallback"
    )
    return {
        "graph_backfill_duration_ms_avg": _avg_duration(backfills),
        "graph_backfill_duration_ms_total": float(
            sum(report.duration_ms for report in backfills)
        ),
        "graph_backfill_run_count": float(len(backfills)),
        "graph_error_count": float(sum(error_codes.values())),
        "graph_operation_failed_count": float(
            sum(1 for report in operation_reports if report.status == "failed")
        ),
        "graph_operational_cost_usd": graph_operational_cost.amount_usd or 0.0,
        "graph_reindex_duration_ms_avg": _avg_duration(reindexes),
        "graph_reindex_duration_ms_total": float(
            sum(report.duration_ms for report in reindexes)
        ),
        "graph_reindex_run_count": float(len(reindexes)),
        "graph_retrieval_fallback_count": float(fallback_count),
        "graph_retrieval_fallback_rate": (
            fallback_count / smoke_count if smoke_count else 0.0
        ),
        "graph_retrieval_latency_ms_avg": _avg_smoke_latency(
            retrieval_smoke_reports
        ),
        "graph_retrieval_no_results_count": float(
            sum(
                1
                for report in retrieval_smoke_reports
                if report.status == "no_results"
            )
        ),
        "graph_retrieval_ready_count": float(
            sum(1 for report in retrieval_smoke_reports if report.status == "ready")
        ),
        "graph_retrieval_smoke_count": float(smoke_count),
    }


def _report_status(
    *,
    quality_report: GraphQualityGateReport,
    operation_reports: tuple[GraphBackfillOperationReport, ...],
    retrieval_smoke_reports: tuple[GraphRetrievalSmokeReport, ...],
) -> EvalStatus:
    if quality_report.status == "failed":
        return "failed"
    if any(report.status != "ready" for report in operation_reports):
        return "failed"
    if any(report.status != "ready" for report in retrieval_smoke_reports):
        return "failed"
    return "passed"


def _error_code_counts(
    operation_reports: tuple[GraphBackfillOperationReport, ...],
    retrieval_smoke_reports: tuple[GraphRetrievalSmokeReport, ...],
) -> Counter[str]:
    counter: Counter[str] = Counter()
    for operation_report in operation_reports:
        if operation_report.error_code is not None:
            counter[operation_report.error_code] += 1
    for retrieval_report in retrieval_smoke_reports:
        if retrieval_report.fallback_reason is not None:
            counter[retrieval_report.fallback_reason] += 1
    return counter


def _serialize_operation_report(
    report: GraphBackfillOperationReport,
) -> dict[str, object]:
    return {
        "project_id": str(report.project_id),
        "backend": report.backend,
        "operation": report.operation,
        "previous_status": report.previous_status,
        "status": report.status,
        "source_watermark": report.source_watermark,
        "duration_ms": report.duration_ms,
        "node_count": report.node_count,
        "relationship_count": report.relationship_count,
        "error_code": report.error_code,
    }


def _serialize_retrieval_smoke_report(
    report: GraphRetrievalSmokeReport,
) -> dict[str, object]:
    return {
        "project_id": str(report.project_id),
        "backend": report.backend,
        "status": report.status,
        "requested_strategy": report.requested_strategy,
        "result_count": report.result_count,
        "graph_result_count": report.graph_result_count,
        "citation_count": report.citation_count,
        "fallback_reason": report.fallback_reason,
        "latency_ms": report.latency_ms,
        "limit": report.limit,
        "chunk_ids": [str(chunk_id) for chunk_id in report.chunk_ids],
        "source_external_ids": list(report.source_external_ids),
    }


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise EvalDatasetError(f"could not read graph evidence report: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvalDatasetError(
            f"could not decode graph evidence report JSON: {path}"
        ) from exc
    if not isinstance(data, dict):
        raise EvalDatasetError(f"graph evidence report must be a JSON object: {path}")
    return data


def _avg_duration(reports: tuple[GraphBackfillOperationReport, ...]) -> float:
    if not reports:
        return 0.0
    return sum(report.duration_ms for report in reports) / len(reports)


def _avg_smoke_latency(reports: tuple[GraphRetrievalSmokeReport, ...]) -> float:
    if not reports:
        return 0.0
    return sum(report.latency_ms for report in reports) / len(reports)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise EvalDatasetError("optional integer fields must not be booleans")
    if isinstance(value, int | float | str | bytes | bytearray):
        return int(value)
    raise EvalDatasetError("optional integer fields must be numeric or strings")


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)


def _sorted_metrics(metrics: dict[str, float]) -> dict[str, float]:
    return {key: metrics[key] for key in sorted(metrics)}
