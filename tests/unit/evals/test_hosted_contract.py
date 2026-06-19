"""Tests del contrato inicial de hosted evals M8."""

from __future__ import annotations

import pytest

from adaptive_rag.evals import (
    EvalCaseResult,
    EvalConfigurationError,
    EvalRunOptions,
    EvalRunReport,
    serialize_eval_report,
    summarize_provider_usage,
    validate_hosted_eval_credentials,
    validate_hosted_eval_options,
)
from adaptive_rag.provider_usage import ProviderCallRecord, ProviderTokenUsage


def test_hosted_eval_options_require_explicit_budget() -> None:
    options = EvalRunOptions(mode="hosted", provider="qwen")

    with pytest.raises(
        EvalConfigurationError,
        match="hosted evals require --max-cost-usd",
    ):
        validate_hosted_eval_options(options)


def test_hosted_eval_options_reject_unknown_provider() -> None:
    options = EvalRunOptions(
        mode="hosted",
        provider="unknown",
        max_cost_usd=0.05,
    )

    with pytest.raises(
        EvalConfigurationError,
        match="unsupported hosted eval provider: unknown",
    ):
        validate_hosted_eval_options(options)


def test_hosted_eval_credentials_fail_before_network() -> None:
    options = EvalRunOptions(mode="hosted", provider="qwen", max_cost_usd=0.05)

    with pytest.raises(
        EvalConfigurationError,
        match="hosted eval provider qwen requires ADAPTIVE_RAG_QWEN_API_KEY",
    ):
        validate_hosted_eval_credentials(
            options,
            qwen_api_key=None,
            qwen_base_url="https://example.test/compatible-mode/v1",
        )


def test_serialize_hosted_report_includes_provider_usage_without_secrets() -> None:
    usage = summarize_provider_usage(
        (
            ProviderCallRecord(
                provider="qwen",
                model="qwen-plus",
                operation="chat",
                outcome="succeeded",
                duration_ms=120,
                usage=ProviderTokenUsage(
                    input_tokens=100,
                    output_tokens=25,
                    total_tokens=125,
                ),
                usage_source="provider_reported",
                estimated_cost_usd=0.0004,
                request_id="req-1",
            ),
            ProviderCallRecord(
                provider="qwen",
                model="qwen-plus",
                operation="chat",
                outcome="blocked",
                duration_ms=2,
                usage=ProviderTokenUsage(),
                usage_source="unavailable",
                estimated_cost_usd=None,
                error_type="ProviderBudgetExceededError",
            ),
        )
    )
    report = EvalRunReport(
        suite_id="hosted-smoke",
        status="failed",
        metrics={"chat_citation_coverage": 0.5},
        thresholds={"chat_citation_coverage": 1.0},
        cases=(
            EvalCaseResult(
                id="chat-alpha",
                kind="chat",
                status="failed",
                metrics={"citation_coverage": 0.5},
                errors=("missing expected evidence: beta",),
            ),
        ),
        mode="hosted",
        provider_usage=usage,
    )

    assert serialize_eval_report(report) == {
        "suite_id": "hosted-smoke",
        "status": "failed",
        "metrics": {"chat_citation_coverage": 0.5},
        "thresholds": {"chat_citation_coverage": 1.0},
        "cases": [
            {
                "id": "chat-alpha",
                "kind": "chat",
                "status": "failed",
                "metrics": {"citation_coverage": 0.5},
                "errors": ["missing expected evidence: beta"],
            }
        ],
        "mode": "hosted",
        "provider_usage": {
            "total_call_count": 2,
            "total_estimated_cost_usd": 0.0004,
            "operations": [
                {
                    "operation": "chat",
                    "provider": "qwen",
                    "model": "qwen-plus",
                    "call_count": 2,
                    "succeeded_count": 1,
                    "failed_count": 0,
                    "blocked_count": 1,
                    "input_tokens": 100,
                    "output_tokens": 25,
                    "total_tokens": 125,
                    "input_count": None,
                    "estimated_cost_usd": 0.0004,
                    "usage_unavailable_count": 1,
                }
            ],
        },
    }

