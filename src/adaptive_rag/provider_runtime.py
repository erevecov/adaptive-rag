"""Configuracion y factories del runtime de providers."""

from __future__ import annotations

from adaptive_rag.chat import ChatRunner, RetrievalGroundedChatRunner
from adaptive_rag.config.settings import Settings, get_settings
from adaptive_rag.embeddings import DenseEmbeddingProvider, FakeDenseEmbeddingProvider


class ProviderConfigurationError(ValueError):
    """Error estable de configuracion para providers live."""


def get_dense_embedding_provider(
    settings: Settings | None = None,
) -> DenseEmbeddingProvider:
    runtime_settings = settings or get_settings()
    _validate_embedding_provider(runtime_settings)
    return FakeDenseEmbeddingProvider()


def get_chat_runner(settings: Settings | None = None) -> ChatRunner:
    runtime_settings = settings or get_settings()
    _validate_chat_provider(runtime_settings)
    return RetrievalGroundedChatRunner()


def _validate_embedding_provider(settings: Settings) -> None:
    if settings.provider_runtime_mode == "fake":
        if settings.embedding_provider != "fake":
            raise ProviderConfigurationError(
                f"embedding provider '{settings.embedding_provider}' requires "
                "live provider runtime mode"
            )
        return

    if settings.embedding_provider != "qwen":
        raise ProviderConfigurationError(
            f"unsupported embedding provider: {settings.embedding_provider}"
        )
    _require_qwen_credentials(settings)
    raise ProviderConfigurationError(
        "qwen embedding provider is not implemented yet"
    )


def _validate_chat_provider(settings: Settings) -> None:
    if settings.provider_runtime_mode == "fake":
        if settings.chat_provider != "fake":
            raise ProviderConfigurationError(
                f"chat provider '{settings.chat_provider}' requires "
                "live provider runtime mode"
            )
        return

    if settings.chat_provider != "qwen":
        raise ProviderConfigurationError(
            f"unsupported chat provider: {settings.chat_provider}"
        )
    _require_qwen_credentials(settings)
    raise ProviderConfigurationError("qwen chat runner is not implemented yet")


def _require_qwen_credentials(settings: Settings) -> None:
    if settings.qwen_api_key is None:
        raise ProviderConfigurationError(
            "ADAPTIVE_RAG_QWEN_API_KEY is required for live provider runtime"
        )
    if not settings.qwen_base_url:
        raise ProviderConfigurationError(
            "ADAPTIVE_RAG_QWEN_BASE_URL is required for live provider runtime"
        )
