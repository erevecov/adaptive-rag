from __future__ import annotations

from uuid import UUID

from adaptive_rag.evals.graph_live_evidence import (
    GraphOperationalCost,
    build_graph_live_evidence_report,
    serialize_graph_live_evidence_report,
)
from adaptive_rag.evals.graph_quality_gate_runner import GraphQualityGateReport
from adaptive_rag.evals.models import EvalRunReport
from adaptive_rag.graph import GraphBackfillOperationReport, GraphRetrievalSmokeReport


def test_graph_live_evidence_report_summarizes_operational_metrics() -> None:
    project_id = UUID("00000000-0000-0000-0000-000000000123")
    backfill = GraphBackfillOperationReport(
        project_id=project_id,
        backend="neo4j",
        operation="backfill",
        previous_status="disabled",
        status="ready",
        source_watermark="chunks:v1",
        duration_ms=1200,
        node_count=10,
        relationship_count=9,
        error_code=None,
    )
    reindex_failure = GraphBackfillOperationReport(
        project_id=project_id,
        backend="neo4j",
        operation="reindex",
        previous_status="stale",
        status="failed",
        source_watermark="chunks:v2",
        duration_ms=500,
        node_count=None,
        relationship_count=None,
        error_code="graph_store_unavailable",
    )
    ready_smoke = GraphRetrievalSmokeReport(
        project_id=project_id,
        backend="neo4j",
        status="ready",
        requested_strategy="graph",
        result_count=2,
        graph_result_count=2,
        citation_count=2,
        fallback_reason=None,
        latency_ms=40,
        limit=2,
        chunk_ids=(UUID("00000000-0000-0000-0000-000000000456"),),
        source_external_ids=("alpha.md",),
    )
    fallback_smoke = GraphRetrievalSmokeReport(
        project_id=project_id,
        backend="neo4j",
        status="fallback",
        requested_strategy="graph",
        result_count=2,
        graph_result_count=0,
        citation_count=2,
        fallback_reason="graph_projection_pending_backfill",
        latency_ms=60,
        limit=2,
        chunk_ids=(),
        source_external_ids=(),
    )

    report = build_graph_live_evidence_report(
        quality_report=_quality_report(),
        operation_reports=(backfill, reindex_failure),
        retrieval_smoke_reports=(ready_smoke, fallback_smoke),
        graph_operational_cost=GraphOperationalCost(
            amount_usd=12.5,
            notes="Neo4j Aura daily estimate",
        ),
    )

    assert report.status == "failed"
    assert report.decision == "hold_default"
    assert report.operational_metrics == {
        "graph_backfill_duration_ms_avg": 1200.0,
        "graph_backfill_duration_ms_total": 1200.0,
        "graph_backfill_run_count": 1.0,
        "graph_error_count": 2.0,
        "graph_operation_failed_count": 1.0,
        "graph_operational_cost_usd": 12.5,
        "graph_reindex_duration_ms_avg": 500.0,
        "graph_reindex_duration_ms_total": 500.0,
        "graph_reindex_run_count": 1.0,
        "graph_retrieval_fallback_count": 1.0,
        "graph_retrieval_fallback_rate": 0.5,
        "graph_retrieval_latency_ms_avg": 50.0,
        "graph_retrieval_no_results_count": 0.0,
        "graph_retrieval_ready_count": 1.0,
        "graph_retrieval_smoke_count": 2.0,
    }
    assert report.error_codes == {
        "graph_projection_pending_backfill": 1,
        "graph_store_unavailable": 1,
    }

    payload = serialize_graph_live_evidence_report(report)
    assert payload["suite_id"] == "m19-live-evidence"
    assert payload["status"] == "failed"
    assert payload["decision"] == "hold_default"
    assert payload["graph_operational_cost"] == {
        "amount_usd": 12.5,
        "currency": "USD",
        "notes": "Neo4j Aura daily estimate",
    }
    assert payload["comparison_metrics"]["graph_provider_cost_delta_usd"] == 0.0
    assert payload["error_codes"] == {
        "graph_projection_pending_backfill": 1,
        "graph_store_unavailable": 1,
    }
    assert payload["operation_reports"][1]["operation"] == "reindex"
    assert payload["retrieval_smoke_reports"][1]["status"] == "fallback"


def _quality_report() -> GraphQualityGateReport:
    dense_report = EvalRunReport(
        suite_id="m19-live-evidence",
        status="passed",
        metrics={"retrieval_hit_rate": 1.0, "retrieval_passed_count": 1.0},
        thresholds={"retrieval_hit_rate": 1.0},
        cases=(),
    )
    graph_report = EvalRunReport(
        suite_id="m19-live-evidence",
        status="passed",
        metrics={"retrieval_hit_rate": 1.0, "retrieval_passed_count": 1.0},
        thresholds={"retrieval_hit_rate": 1.0},
        cases=(),
    )
    return GraphQualityGateReport(
        suite_id="m19-live-evidence",
        status="passed",
        decision="hold_default",
        dense_baseline=dense_report,
        graph=graph_report,
        comparison_metrics={
            "graph_provider_cost_delta_usd": 0.0,
            "graph_retrieval_hit_rate": 1.0,
            "graph_retrieval_hit_rate_delta": 0.0,
        },
        comparison_cases=(),
    )
