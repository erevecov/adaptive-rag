"""Limits, retry math, redaction, and execution-context behavior."""

from __future__ import annotations

from uuid import uuid4

import pytest

from adaptive_rag.jobs import (
    JobCancelled,
    JobContext,
    JobPayloadTooLargeError,
    RetryPolicy,
    ensure_json_size,
    redact_secret_keys,
    retry_delay_seconds,
    truncate_utf8,
)


@pytest.mark.parametrize("retry_count,upper", [(0, 1.0), (1, 2.0), (6, 60.0)])
def test_full_jitter_is_bounded(retry_count: int, upper: float) -> None:
    delay = retry_delay_seconds(
        RetryPolicy(max_retries=8), retry_count, random_value=0.5
    )
    assert delay == upper * 0.5


@pytest.mark.parametrize("random_value", [-0.01, 1.01])
def test_full_jitter_rejects_random_values_outside_unit_interval(
    random_value: float,
) -> None:
    with pytest.raises(ValueError, match="random_value"):
        retry_delay_seconds(RetryPolicy(), 0, random_value=random_value)


def test_json_size_uses_canonical_utf8_bytes() -> None:
    assert ensure_json_size({"é": "✓"}, limit_bytes=12) == 12
    with pytest.raises(JobPayloadTooLargeError):
        ensure_json_size({"é": "✓"}, limit_bytes=11)


def test_redaction_is_recursive_and_does_not_mutate_input() -> None:
    raw = {
        "api_key": "top",
        "nested": [{"access_token": "inner"}, {"safe": "value"}],
    }

    redacted = redact_secret_keys(raw)

    assert redacted == {
        "api_key": "[REDACTED]",
        "nested": [{"access_token": "[REDACTED]"}, {"safe": "value"}],
    }
    assert raw["api_key"] == "top"


def test_utf8_truncation_never_splits_a_code_point() -> None:
    assert truncate_utf8("áéí", limit_bytes=5) == "áé"


def test_job_context_reports_progress_and_confirms_cancellation() -> None:
    progress: list[dict[str, object]] = []
    cancelled = False

    def is_cancel_requested() -> bool:
        return cancelled

    context = JobContext(
        job_id=uuid4(),
        attempt_id=uuid4(),
        workspace_id=None,
        idempotency_key="echo-1",
        is_cancel_requested_callback=is_cancel_requested,
        report_progress_callback=progress.append,
        is_lease_healthy_callback=lambda: True,
    )

    context.report_progress({"completed": 1})
    assert progress == [{"completed": 1}]
    assert context.is_lease_healthy() is True

    cancelled = True
    with pytest.raises(JobCancelled):
        context.raise_if_cancelled()
