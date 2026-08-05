"""CI-safe eval_routing suite for the rule-based query router."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from adaptive_rag.routing import QueryRoute, RuleBasedQueryRouter

EvalRoutingStatus = Literal["passed", "failed"]


@dataclass(frozen=True, slots=True)
class RoutingEvalCase:
    case_id: str
    query: str
    expected_route: QueryRoute
    graph_ready: bool = False


@dataclass(frozen=True, slots=True)
class RoutingEvalCaseResult:
    case_id: str
    expected_route: QueryRoute
    observed_route: QueryRoute
    reason: str
    status: EvalRoutingStatus


@dataclass(frozen=True, slots=True)
class RoutingEvalReport:
    suite_id: str
    status: EvalRoutingStatus
    passed: int
    failed: int
    cases: tuple[RoutingEvalCaseResult, ...]


DEFAULT_ROUTING_CASES: tuple[RoutingEvalCase, ...] = (
    RoutingEvalCase("skip-hello", "Hello!", "skip_retrieval"),
    RoutingEvalCase("skip-thanks", "thanks", "skip_retrieval"),
    RoutingEvalCase(
        "default-factual", "What is Adaptive RAG indexing?", "dense_sparse"
    ),
    RoutingEvalCase(
        "graph-ready",
        "How is Project A related to Service B?",
        "graph",
        graph_ready=True,
    ),
    RoutingEvalCase(
        "graph-not-ready-fallback",
        "How is Project A related to Service B?",
        "dense_sparse",
        graph_ready=False,
    ),
)


def run_routing_eval_suite(
    cases: tuple[RoutingEvalCase, ...] = DEFAULT_ROUTING_CASES,
    *,
    router: RuleBasedQueryRouter | None = None,
) -> RoutingEvalReport:
    active_router = router or RuleBasedQueryRouter()
    results: list[RoutingEvalCaseResult] = []
    for case in cases:
        decision = active_router.route(case.query, graph_ready=case.graph_ready)
        status: EvalRoutingStatus = (
            "passed" if decision.route == case.expected_route else "failed"
        )
        results.append(
            RoutingEvalCaseResult(
                case_id=case.case_id,
                expected_route=case.expected_route,
                observed_route=decision.route,
                reason=decision.reason,
                status=status,
            )
        )
    failed = sum(1 for item in results if item.status == "failed")
    passed = len(results) - failed
    return RoutingEvalReport(
        suite_id="eval_routing",
        status="passed" if failed == 0 else "failed",
        passed=passed,
        failed=failed,
        cases=tuple(results),
    )


def serialize_routing_eval_report(report: RoutingEvalReport) -> dict[str, Any]:
    return {
        "suite_id": report.suite_id,
        "status": report.status,
        "passed": report.passed,
        "failed": report.failed,
        "cases": [
            {
                "case_id": case.case_id,
                "expected_route": case.expected_route,
                "observed_route": case.observed_route,
                "reason": case.reason,
                "status": case.status,
            }
            for case in report.cases
        ],
    }
