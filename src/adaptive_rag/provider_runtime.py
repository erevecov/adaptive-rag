"""Configuracion y factories del runtime de providers."""

from __future__ import annotations

from adaptive_rag.chat import ChatRunner, QwenChatRunner, RetrievalGroundedChatRunner
from adaptive_rag.chat.qwen import QwenHTTPChatClient
from adaptive_rag.config.settings import Settings, get_settings
from adaptive_rag.embeddings import (
    DenseEmbeddingProvider,
    FakeDenseEmbeddingProvider,
    QwenDenseEmbeddingProvider,
    QwenHTTPEmbeddingClient,
)
from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderBudgetGuard,
    ProviderPriceCatalog,
)


class ProviderConfigurationError(ValueError):
    """Error estable de configuracion para providers live."""


def get_dense_embedding_provider(
    settings: Settings | None = None,
) -> DenseEmbeddingProvider:
    runtime_settings = settings or get_settings()
    return _build_embedding_provider(runtime_settings)


def get_chat_runner(settings: Settings | None = None) -> ChatRunner:
    runtime_settings = settings or get_settings()
    return _build_chat_runner(runtime_settings)


def _build_embedding_provider(settings: Settings) -> DenseEmbeddingProvider:
    if settings.provider_runtime_mode == "fake":
        if settings.embedding_provider != "fake":
            raise ProviderConfigurationError(
                f"embedding provider '{settings.embedding_provider}' requires "
                "live provider runtime mode"
            )
        return FakeDenseEmbeddingProvider()

    if settings.embedding_provider != "qwen":
        raise ProviderConfigurationError(
            f"unsupported embedding provider: {settings.embedding_provider}"
        )
    _require_qwen_credentials(settings)
    if not settings.embedding_model or settings.embedding_model == "fake-embedding-v1":
        raise ProviderConfigurationError(
            "ADAPTIVE_RAG_EMBEDDING_MODEL must be set for qwen"
        )
    if settings.qwen_api_key is None or settings.qwen_base_url is None:
        raise ProviderConfigurationError("qwen credentials were not validated")
    return QwenDenseEmbeddingProvider(
        model_name=settings.embedding_model,
        client=QwenHTTPEmbeddingClient(
            api_key=settings.qwen_api_key.get_secret_value(),
            base_url=settings.qwen_base_url,
            timeout_seconds=settings.provider_timeout_seconds,
            max_retries=settings.provider_max_retries,
            usage_tracker=InMemoryProviderUsageTracker(),
            price_catalog=_provider_price_catalog(settings),
            budget_guard=_provider_budget_guard(settings),
        ),
    )


def _build_chat_runner(settings: Settings) -> ChatRunner:
    if settings.provider_runtime_mode == "fake":
        if settings.chat_provider != "fake":
            raise ProviderConfigurationError(
                f"chat provider '{settings.chat_provider}' requires "
                "live provider runtime mode"
            )
        return RetrievalGroundedChatRunner()

    if settings.chat_provider != "qwen":
        raise ProviderConfigurationError(
            f"unsupported chat provider: {settings.chat_provider}"
        )
    _require_qwen_credentials(settings)
    if not settings.chat_model or settings.chat_model == "retrieval-grounded-local-v1":
        raise ProviderConfigurationError("ADAPTIVE_RAG_CHAT_MODEL must be set for qwen")
    if settings.qwen_api_key is None or settings.qwen_base_url is None:
        raise ProviderConfigurationError("qwen credentials were not validated")
    return QwenChatRunner(
        model_name=settings.chat_model,
        client=QwenHTTPChatClient(
            api_key=settings.qwen_api_key.get_secret_value(),
            base_url=settings.qwen_base_url,
            timeout_seconds=settings.provider_timeout_seconds,
            max_retries=settings.provider_max_retries,
            usage_tracker=InMemoryProviderUsageTracker(),
            price_catalog=_provider_price_catalog(settings),
            budget_guard=_provider_budget_guard(settings),
        ),
    )


def _require_qwen_credentials(settings: Settings) -> None:
    if settings.qwen_api_key is None:
        raise ProviderConfigurationError(
            "ADAPTIVE_RAG_QWEN_API_KEY is required for live provider runtime"
        )
    if not settings.qwen_base_url:
        raise ProviderConfigurationError(
            "ADAPTIVE_RAG_QWEN_BASE_URL is required for live provider runtime"
        )


def _provider_budget_guard(settings: Settings) -> ProviderBudgetGuard | None:
    if settings.provider_max_cost_usd is None:
        return None
    return ProviderBudgetGuard(max_cost_usd=settings.provider_max_cost_usd)


def _provider_price_catalog(settings: Settings) -> ProviderPriceCatalog:
    return ProviderPriceCatalog(
        chat_input_price_per_million_tokens_usd=(
            settings.provider_chat_input_price_per_million_tokens_usd
        ),
        chat_output_price_per_million_tokens_usd=(
            settings.provider_chat_output_price_per_million_tokens_usd
        ),
        embedding_input_price_per_million_tokens_usd=(
            settings.provider_embedding_input_price_per_million_tokens_usd
        ),
    )
