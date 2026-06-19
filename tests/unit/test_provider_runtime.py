import pytest

from adaptive_rag import provider_runtime
from adaptive_rag.api import dependencies as api_dependencies
from adaptive_rag.chat import RetrievalGroundedChatRunner
from adaptive_rag.cli import dependencies as cli_dependencies
from adaptive_rag.config.settings import Settings
from adaptive_rag.embeddings import FakeDenseEmbeddingProvider
from adaptive_rag.provider_runtime import (
    ProviderConfigurationError,
    get_chat_runner,
    get_dense_embedding_provider,
)


def _settings(**overrides):
    return Settings(_env_file=None, **overrides)


def test_provider_runtime_defaults_to_fake_without_credentials():
    settings = _settings()

    provider = get_dense_embedding_provider(settings)
    runner = get_chat_runner(settings)

    assert settings.provider_runtime_mode == "fake"
    assert isinstance(provider, FakeDenseEmbeddingProvider)
    assert isinstance(runner, RetrievalGroundedChatRunner)


def test_fake_runtime_rejects_non_fake_embedding_provider():
    settings = _settings(embedding_provider="qwen")

    with pytest.raises(
        ProviderConfigurationError,
        match="embedding provider 'qwen' requires live provider runtime mode",
    ):
        get_dense_embedding_provider(settings)


def test_fake_runtime_rejects_non_fake_chat_provider():
    settings = _settings(chat_provider="qwen")

    with pytest.raises(
        ProviderConfigurationError,
        match="chat provider 'qwen' requires live provider runtime mode",
    ):
        get_chat_runner(settings)


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


def test_api_and_cli_dependencies_use_runtime_factories(monkeypatch):
    settings = _settings()
    monkeypatch.setattr(provider_runtime, "get_settings", lambda: settings)

    assert isinstance(
        api_dependencies.get_dense_embedding_provider(),
        FakeDenseEmbeddingProvider,
    )
    assert isinstance(api_dependencies.get_chat_runner(), RetrievalGroundedChatRunner)
    assert isinstance(
        cli_dependencies.get_cli_dense_embedding_provider(),
        FakeDenseEmbeddingProvider,
    )
    assert isinstance(
        cli_dependencies.get_cli_chat_runner(),
        RetrievalGroundedChatRunner,
    )


def test_api_and_cli_dependencies_propagate_runtime_configuration_errors(
    monkeypatch,
):
    settings = _settings(provider_runtime_mode="live", embedding_provider="qwen")
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
