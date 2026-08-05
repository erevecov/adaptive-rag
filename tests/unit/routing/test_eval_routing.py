"""CI-safe eval_routing suite."""

from __future__ import annotations

from adaptive_rag.evals.routing_runner import (
    run_routing_eval_suite,
    serialize_routing_eval_report,
)


def test_eval_routing_default_suite_passes() -> None:
    report = run_routing_eval_suite()
    assert report.status == "passed"
    assert report.failed == 0
    payload = serialize_routing_eval_report(report)
    assert all(case["status"] == "passed" for case in payload["cases"])
