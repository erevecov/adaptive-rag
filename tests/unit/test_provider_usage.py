from __future__ import annotations

import pytest

from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderBudgetExceededError,
    ProviderBudgetGuard,
    ProviderCallRecord,
    ProviderPriceCatalog,
    ProviderTokenUsage,
    estimate_cost_usd,
)


def test_estimate_cost_uses_configured_chat_prices() -> None:
    cost = estimate_cost_usd(
        operation="chat",
        usage=ProviderTokenUsage(input_tokens=1_000, output_tokens=500),
        price_catalog=ProviderPriceCatalog(
            chat_input_price_per_million_tokens_usd=2.0,
            chat_output_price_per_million_tokens_usd=6.0,
        ),
    )

    assert cost == 0.005


def test_estimate_cost_returns_none_without_configured_price() -> None:
    cost = estimate_cost_usd(
        operation="embedding",
        usage=ProviderTokenUsage(input_tokens=1_000),
        price_catalog=ProviderPriceCatalog(),
    )

    assert cost is None


def test_budget_guard_blocks_cost_above_configured_limit() -> None:
    guard = ProviderBudgetGuard(max_cost_usd=0.01)
    record = ProviderCallRecord(
        provider="qwen",
        model="qwen-plus",
        operation="chat",
        outcome="succeeded",
        duration_ms=12,
        usage=ProviderTokenUsage(input_tokens=10_000, output_tokens=10_000),
        usage_source="provider_reported",
        estimated_cost_usd=0.02,
    )

    with pytest.raises(
        ProviderBudgetExceededError,
        match="provider budget exceeded: estimated 0.02 USD exceeds limit 0.01 USD",
    ):
        guard.enforce(record)


def test_usage_tracker_keeps_structured_records() -> None:
    tracker = InMemoryProviderUsageTracker()
    record = ProviderCallRecord(
        provider="qwen",
        model="text-embedding-v4",
        operation="embedding",
        outcome="succeeded",
        duration_ms=5,
        usage=ProviderTokenUsage(input_tokens=42),
        usage_source="provider_reported",
        estimated_cost_usd=None,
        request_id="req_123",
    )

    tracker.record(record)

    assert tracker.records == (record,)
