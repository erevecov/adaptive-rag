import pytest

from adaptive_rag import provider_runtime
from adaptive_rag.api import dependencies as api_dependencies
from adaptive_rag.chat import QwenChatRunner, RetrievalGroundedChatRunner
from adaptive_rag.cli import dependencies as cli_dependencies
from adaptive_rag.config.settings import Settings
from adaptive_rag.embeddings import (
    FakeDenseEmbeddingProvider,
    FakeSparseEmbeddingProvider,
    QwenDenseEmbeddingProvider,
    QwenSparseEmbeddingProvider,
)
from adaptive_rag.provider_runtime import (
    ProviderConfigurationError,
    get_chat_runner,
    get_contextualizer,
    get_dense_embedding_provider,
    get_rerank_provider,
    get_sparse_embedding_provider,
)
from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderBudgetGuard,
    ProviderPriceCatalog,
)
from adaptive_rag.rerank import (
    FakeRerankProvider,
    QwenHTTPRerankClient,
    QwenRerankProvider,
)


def _settings(**overrides):
    return Settings(_env_file=None, **overrides)


def test_provider_runtime_public_facade_exports_expected_names():
    assert provider_runtime.ProviderConfigurationError is ProviderConfigurationError
    assert provider_runtime.get_chat_runner is get_chat_runner
    assert provider_runtime.get_contextualizer is get_contextualizer
    assert provider_runtime.get_dense_embedding_provider is get_dense_embedding_provider
    assert (
        provider_runtime.get_sparse_embedding_provider
        is get_sparse_embedding_provider
    )
    assert provider_runtime.get_rerank_provider is get_rerank_provider


def test_provider_runtime_defaults_to_fake_without_credentials():
    settings = _settings()

    provider = get_dense_embedding_provider(settings)
    sparse_provider = get_sparse_embedding_provider(settings)
    runner = get_chat_runner(settings)
    reranker = get_rerank_provider(settings)

    assert settings.provider_runtime_mode == "fake"
    assert isinstance(provider, FakeDenseEmbeddingProvider)
    assert isinstance(sparse_provider, FakeSparseEmbeddingProvider)
    assert isinstance(runner, RetrievalGroundedChatRunner)
    assert isinstance(reranker, FakeRerankProvider)


def test_fake_runtime_rejects_non_fake_embedding_provider():
    settings = _settings(embedding_provider="qwen")

    with pytest.raises(
        ProviderConfigurationError,
        match="embedding provider 'qwen' requires live provider runtime mode",
    ):
        get_dense_embedding_provider(settings)


def test_fake_runtime_rejects_non_fake_sparse_embedding_provider():
    settings = _settings(sparse_embedding_provider="qwen")

    with pytest.raises(
        ProviderConfigurationError,
        match="sparse embedding provider 'qwen' requires live provider runtime mode",
    ):
        get_sparse_embedding_provider(settings)


def test_fake_runtime_rejects_non_fake_chat_provider():
    settings = _settings(chat_provider="qwen")

    with pytest.raises(
        ProviderConfigurationError,
        match="chat provider 'qwen' requires live provider runtime mode",
    ):
        get_chat_runner(settings)


def test_fake_runtime_rejects_non_fake_rerank_provider():
    settings = _settings(rerank_provider="qwen")

    with pytest.raises(
        ProviderConfigurationError,
        match="rerank provider 'qwen' requires live provider runtime mode",
    ):
        get_rerank_provider(settings)


def test_unknown_live_provider_fails_before_client_creation():
    settings = _settings(
        provider_runtime_mode="live",
        embedding_provider="unknown",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/v1",
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="unsupported embedding provider: unknown",
    ):
        get_dense_embedding_provider(settings)


def test_unknown_live_sparse_provider_fails_before_client_creation():
    settings = _settings(
        provider_runtime_mode="live",
        sparse_embedding_provider="unknown",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/api/v1/services/embeddings/text-embedding",
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="unsupported sparse embedding provider: unknown",
    ):
        get_sparse_embedding_provider(settings)


def test_unknown_live_rerank_provider_fails_before_client_creation():
    settings = _settings(
        provider_runtime_mode="live",
        rerank_provider="unknown",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/v1",
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="unsupported rerank provider: unknown",
    ):
        get_rerank_provider(settings)


def test_live_provider_requires_credentials_before_network_clients():
    settings = _settings(
        provider_runtime_mode="live",
        embedding_provider="qwen",
        embedding_model="qwen-embedding-live-v1",
        qwen_api_key=None,
        qwen_base_url="https://example.test/v1",
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="ADAPTIVE_RAG_QWEN_API_KEY is required for live provider runtime",
    ):
        get_dense_embedding_provider(settings)


def test_live_qwen_sparse_provider_requires_credentials_before_network_clients():
    settings = _settings(
        provider_runtime_mode="live",
        sparse_embedding_provider="qwen",
        sparse_embedding_model="text-embedding-v4",
        qwen_api_key=None,
        qwen_base_url="https://example.test/api/v1/services/embeddings/text-embedding",
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="ADAPTIVE_RAG_QWEN_API_KEY is required for live provider runtime",
    ):
        get_sparse_embedding_provider(settings)


def test_live_qwen_rerank_provider_requires_credentials_before_network_clients():
    settings = _settings(
        provider_runtime_mode="live",
        rerank_provider="qwen",
        rerank_model="qwen3-rerank",
        qwen_api_key=None,
        qwen_base_url="https://example.test/v1",
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="ADAPTIVE_RAG_QWEN_API_KEY is required for live provider runtime",
    ):
        get_rerank_provider(settings)


def test_live_qwen_embedding_provider_requires_live_model():
    settings = _settings(
        provider_runtime_mode="live",
        embedding_provider="qwen",
        embedding_model="fake-embedding-v1",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/v1",
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="ADAPTIVE_RAG_EMBEDDING_MODEL must be set for qwen",
    ):
        get_dense_embedding_provider(settings)


def test_live_qwen_sparse_provider_requires_live_model():
    settings = _settings(
        provider_runtime_mode="live",
        sparse_embedding_provider="qwen",
        sparse_embedding_model="fake-sparse-embedding-v1",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/api/v1/services/embeddings/text-embedding",
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="ADAPTIVE_RAG_SPARSE_EMBEDDING_MODEL must be set for qwen",
    ):
        get_sparse_embedding_provider(settings)


def test_live_qwen_rerank_provider_requires_live_model():
    settings = _settings(
        provider_runtime_mode="live",
        rerank_provider="qwen",
        rerank_model="fake-rerank-v1",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/v1",
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="ADAPTIVE_RAG_RERANK_MODEL must be set for qwen",
    ):
        get_rerank_provider(settings)


def test_live_qwen_embedding_provider_is_configured_without_network_call():
    settings = _settings(
        provider_runtime_mode="live",
        embedding_provider="qwen",
        embedding_model="text-embedding-v4",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/v1",
        provider_timeout_seconds=7.5,
        provider_max_retries=3,
    )

    provider = get_dense_embedding_provider(settings)

    assert isinstance(provider, QwenDenseEmbeddingProvider)
    assert provider.provider_name == "qwen"
    assert provider.model_name == "text-embedding-v4"
    assert provider.dimensions == 1024


def test_live_qwen_sparse_provider_is_configured_without_network_call():
    settings = _settings(
        provider_runtime_mode="live",
        sparse_embedding_provider="qwen",
        sparse_embedding_model="text-embedding-v4",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/api/v1/services/embeddings/text-embedding",
        provider_timeout_seconds=7.5,
        provider_max_retries=3,
    )

    provider = get_sparse_embedding_provider(settings)

    assert isinstance(provider, QwenSparseEmbeddingProvider)
    assert provider.provider_name == "qwen"
    assert provider.model_name == "text-embedding-v4"
    assert provider.dimensions == 1024


def test_live_qwen_rerank_provider_is_configured_without_network_call():
    settings = _settings(
        provider_runtime_mode="live",
        rerank_provider="qwen",
        rerank_model="qwen3-rerank",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/v1",
        provider_timeout_seconds=7.5,
        provider_max_retries=3,
    )

    reranker = get_rerank_provider(settings)

    assert isinstance(reranker, QwenRerankProvider)
    assert reranker.provider_name == "qwen"
    assert reranker.model_name == "qwen3-rerank"
    assert isinstance(reranker.client, QwenHTTPRerankClient)


def test_live_qwen_embedding_provider_receives_budget_and_price_config():
    settings = _settings(
        provider_runtime_mode="live",
        embedding_provider="qwen",
        embedding_model="text-embedding-v4",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/v1",
        provider_max_cost_usd=0.01,
        provider_embedding_input_price_per_million_tokens_usd=0.13,
    )

    provider = get_dense_embedding_provider(settings)

    assert isinstance(provider, QwenDenseEmbeddingProvider)
    assert isinstance(provider.client.budget_guard, ProviderBudgetGuard)
    assert provider.client.budget_guard.max_cost_usd == 0.01
    assert isinstance(provider.client.usage_tracker, InMemoryProviderUsageTracker)
    assert isinstance(provider.client.price_catalog, ProviderPriceCatalog)
    assert (
        provider.client.price_catalog.embedding_input_price_per_million_tokens_usd
        == 0.13
    )


def test_live_qwen_sparse_provider_receives_budget_and_price_config():
    settings = _settings(
        provider_runtime_mode="live",
        sparse_embedding_provider="qwen",
        sparse_embedding_model="text-embedding-v4",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/api/v1/services/embeddings/text-embedding",
        provider_max_cost_usd=0.01,
        provider_embedding_input_price_per_million_tokens_usd=0.13,
    )

    provider = get_sparse_embedding_provider(settings)

    assert isinstance(provider, QwenSparseEmbeddingProvider)
    assert isinstance(provider.client.budget_guard, ProviderBudgetGuard)
    assert provider.client.budget_guard.max_cost_usd == 0.01
    assert isinstance(provider.client.usage_tracker, InMemoryProviderUsageTracker)
    assert isinstance(provider.client.price_catalog, ProviderPriceCatalog)
    assert (
        provider.client.price_catalog.embedding_input_price_per_million_tokens_usd
        == 0.13
    )


def test_live_qwen_rerank_provider_receives_budget_and_price_config():
    settings = _settings(
        provider_runtime_mode="live",
        rerank_provider="qwen",
        rerank_model="qwen3-rerank",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/v1",
        provider_max_cost_usd=0.01,
        provider_rerank_input_price_per_million_tokens_usd=0.08,
    )

    reranker = get_rerank_provider(settings)

    assert isinstance(reranker, QwenRerankProvider)
    assert isinstance(reranker.client, QwenHTTPRerankClient)
    assert isinstance(reranker.client.budget_guard, ProviderBudgetGuard)
    assert reranker.client.budget_guard.max_cost_usd == 0.01
    assert isinstance(reranker.client.usage_tracker, InMemoryProviderUsageTracker)
    assert isinstance(reranker.client.price_catalog, ProviderPriceCatalog)
    assert (
        reranker.client.price_catalog.rerank_input_price_per_million_tokens_usd
        == 0.08
    )


def test_live_provider_requires_base_url_before_network_clients():
    settings = _settings(
        provider_runtime_mode="live",
        chat_provider="qwen",
        chat_model="qwen-chat-live-v1",
        qwen_api_key="sk-test",
        qwen_base_url=None,
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="ADAPTIVE_RAG_QWEN_BASE_URL is required for live provider runtime",
    ):
        get_chat_runner(settings)


def test_live_rerank_provider_requires_base_url_before_network_clients():
    settings = _settings(
        provider_runtime_mode="live",
        rerank_provider="qwen",
        rerank_model="qwen3-rerank",
        qwen_api_key="sk-test",
        qwen_base_url=None,
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="ADAPTIVE_RAG_QWEN_BASE_URL is required for live provider runtime",
    ):
        get_rerank_provider(settings)


def test_live_qwen_chat_runner_requires_live_model():
    settings = _settings(
        provider_runtime_mode="live",
        chat_provider="qwen",
        chat_model="retrieval-grounded-local-v1",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/v1",
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="ADAPTIVE_RAG_CHAT_MODEL must be set for qwen",
    ):
        get_chat_runner(settings)


def test_live_qwen_chat_runner_is_configured_without_network_call():
    settings = _settings(
        provider_runtime_mode="live",
        chat_provider="qwen",
        chat_model="qwen-plus",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/v1",
        provider_timeout_seconds=7.5,
        provider_max_retries=3,
    )

    runner = get_chat_runner(settings)

    assert isinstance(runner, QwenChatRunner)
    assert runner.provider_name == "qwen"
    assert runner.model_name == "qwen-plus"


def test_live_qwen_chat_runner_receives_budget_and_price_config():
    settings = _settings(
        provider_runtime_mode="live",
        chat_provider="qwen",
        chat_model="qwen-plus",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/v1",
        provider_max_cost_usd=0.01,
        provider_chat_input_price_per_million_tokens_usd=2.0,
        provider_chat_output_price_per_million_tokens_usd=6.0,
    )

    runner = get_chat_runner(settings)

    assert isinstance(runner, QwenChatRunner)
    assert isinstance(runner.client.budget_guard, ProviderBudgetGuard)
    assert runner.client.budget_guard.max_cost_usd == 0.01
    assert isinstance(runner.client.usage_tracker, InMemoryProviderUsageTracker)
    assert isinstance(runner.client.price_catalog, ProviderPriceCatalog)
    assert runner.client.price_catalog.chat_input_price_per_million_tokens_usd == 2.0
    assert runner.client.price_catalog.chat_output_price_per_million_tokens_usd == 6.0


def test_live_qwen_runtime_can_share_usage_tracker():
    settings = _settings(
        provider_runtime_mode="live",
        embedding_provider="qwen",
        embedding_model="text-embedding-v4",
        chat_provider="qwen",
        chat_model="qwen-plus",
        qwen_api_key="sk-test",
        qwen_base_url="https://example.test/v1",
    )
    tracker = InMemoryProviderUsageTracker()

    provider = get_dense_embedding_provider(settings, usage_tracker=tracker)
    sparse_provider = get_sparse_embedding_provider(
        settings.model_copy(
            update={
                "sparse_embedding_provider": "qwen",
                "sparse_embedding_model": "text-embedding-v4",
            }
        ),
        usage_tracker=tracker,
    )
    runner = get_chat_runner(settings, usage_tracker=tracker)
    reranker = get_rerank_provider(
        settings.model_copy(
            update={
                "rerank_provider": "qwen",
                "rerank_model": "qwen3-rerank",
            }
        ),
        usage_tracker=tracker,
    )

    assert isinstance(provider, QwenDenseEmbeddingProvider)
    assert isinstance(sparse_provider, QwenSparseEmbeddingProvider)
    assert isinstance(runner, QwenChatRunner)
    assert isinstance(reranker, QwenRerankProvider)
    assert provider.client.usage_tracker is tracker
    assert sparse_provider.client.usage_tracker is tracker
    assert runner.client.usage_tracker is tracker
    assert reranker.client.usage_tracker is tracker


def test_api_and_cli_dependencies_use_runtime_factories(monkeypatch):
    settings = _settings()
    monkeypatch.setattr(provider_runtime, "get_settings", lambda: settings)

    assert isinstance(
        api_dependencies.get_dense_embedding_provider(),
        FakeDenseEmbeddingProvider,
    )
    assert isinstance(
        api_dependencies.get_sparse_embedding_provider(),
        FakeSparseEmbeddingProvider,
    )
    assert isinstance(api_dependencies.get_chat_runner(), RetrievalGroundedChatRunner)
    assert isinstance(
        cli_dependencies.get_cli_dense_embedding_provider(),
        FakeDenseEmbeddingProvider,
    )
    assert isinstance(
        cli_dependencies.get_cli_sparse_embedding_provider(),
        FakeSparseEmbeddingProvider,
    )
    assert isinstance(
        cli_dependencies.get_cli_chat_runner(),
        RetrievalGroundedChatRunner,
    )


def test_api_and_cli_dependencies_propagate_runtime_configuration_errors(
    monkeypatch,
):
    settings = _settings(
        provider_runtime_mode="live",
        embedding_provider="qwen",
        sparse_embedding_provider="qwen",
        sparse_embedding_model="text-embedding-v4",
    )
    monkeypatch.setattr(provider_runtime, "get_settings", lambda: settings)

    with pytest.raises(
        ProviderConfigurationError,
        match="ADAPTIVE_RAG_QWEN_API_KEY is required",
    ):
        api_dependencies.get_dense_embedding_provider()

    with pytest.raises(
        ProviderConfigurationError,
        match="ADAPTIVE_RAG_QWEN_API_KEY is required",
    ):
        cli_dependencies.get_cli_dense_embedding_provider()

    with pytest.raises(
        ProviderConfigurationError,
        match="ADAPTIVE_RAG_QWEN_API_KEY is required",
    ):
        cli_dependencies.get_cli_sparse_embedding_provider()
