"""Focused tests for optional provider construction in API dependencies."""

from __future__ import annotations

import pytest

from adaptive_rag.api import dependencies
from adaptive_rag.provider_runtime import ProviderConfigurationError
from adaptive_rag.provider_usage import InMemoryProviderUsageTracker
from adaptive_rag.rerank import FakeRerankProvider


def test_rerank_provider_factory_degrades_configuration_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_configuration_error() -> FakeRerankProvider:
        raise ProviderConfigurationError("missing_provider_secret")

    monkeypatch.setattr(
        dependencies,
        "get_runtime_rerank_provider",
        raise_configuration_error,
    )

    factory = dependencies.get_rerank_provider_factory(
        usage_tracker=InMemoryProviderUsageTracker()
    )

    assert factory() is None


def test_rerank_provider_factory_preserves_configured_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeRerankProvider()
    monkeypatch.setattr(
        dependencies,
        "get_runtime_rerank_provider",
        lambda: provider,
    )

    factory = dependencies.get_rerank_provider_factory(
        usage_tracker=InMemoryProviderUsageTracker()
    )

    assert factory() is provider


def test_rerank_provider_factory_propagates_unexpected_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_unexpected_error() -> FakeRerankProvider:
        raise RuntimeError("programming error")

    monkeypatch.setattr(
        dependencies,
        "get_runtime_rerank_provider",
        raise_unexpected_error,
    )
    factory = dependencies.get_rerank_provider_factory(
        usage_tracker=InMemoryProviderUsageTracker()
    )

    with pytest.raises(RuntimeError, match="programming error"):
        factory()
