"""Runtime provider factories."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.chat import ChatRunner, QwenChatRunner, RetrievalGroundedChatRunner
from adaptive_rag.chat.qwen import QwenHTTPChatClient
from adaptive_rag.config.settings import Settings, get_settings
from adaptive_rag.contextualization import Contextualizer, DeterministicContextualizer
from adaptive_rag.embeddings import (
    DenseEmbeddingProvider,
    FakeDenseEmbeddingProvider,
    FakeSparseEmbeddingProvider,
    QwenDenseEmbeddingProvider,
    QwenHTTPEmbeddingClient,
    QwenSparseEmbeddingProvider,
    SparseEmbeddingProvider,
)
from adaptive_rag.provider_secrets import ProviderSecretStore
from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderBudgetGuard,
    ProviderPriceCatalog,
    ProviderUsageTracker,
)
from adaptive_rag.rerank import (
    FakeRerankProvider,
    QwenHTTPRerankClient,
    QwenRerankProvider,
    RerankProvider,
)
from adaptive_rag.runtime.resolution import (
    ProviderConfigurationError,
    ResolvedRuntimeSlot,
    _resolve_persisted_slot,
)


def get_dense_embedding_provider(
    settings: Settings | None = None,
    *,
    project_id: UUID | None = None,
    secret_store: ProviderSecretStore | None = None,
    session: Session | None = None,
    usage_tracker: ProviderUsageTracker | None = None,
) -> DenseEmbeddingProvider:
    runtime_settings = settings or get_settings()
    resolved = _resolve_persisted_slot(
        "dense_embedding",
        runtime_settings,
        project_id=project_id,
        secret_store=secret_store,
        session=session,
    )
    if resolved is not None:
        return _build_resolved_dense_embedding_provider(
            resolved,
            runtime_settings,
            usage_tracker=usage_tracker,
        )
    return _build_embedding_provider(runtime_settings, usage_tracker=usage_tracker)


def get_sparse_embedding_provider(
    settings: Settings | None = None,
    *,
    project_id: UUID | None = None,
    secret_store: ProviderSecretStore | None = None,
    session: Session | None = None,
    usage_tracker: ProviderUsageTracker | None = None,
) -> SparseEmbeddingProvider:
    runtime_settings = settings or get_settings()
    resolved = _resolve_persisted_slot(
        "sparse_embedding",
        runtime_settings,
        project_id=project_id,
        secret_store=secret_store,
        session=session,
    )
    if resolved is not None:
        return _build_resolved_sparse_embedding_provider(
            resolved,
            runtime_settings,
            usage_tracker=usage_tracker,
        )
    return _build_sparse_embedding_provider(
        runtime_settings,
        usage_tracker=usage_tracker,
    )


def get_chat_runner(
    settings: Settings | None = None,
    *,
    project_id: UUID | None = None,
    secret_store: ProviderSecretStore | None = None,
    session: Session | None = None,
    usage_tracker: ProviderUsageTracker | None = None,
) -> ChatRunner:
    runtime_settings = settings or get_settings()
    resolved = _resolve_persisted_slot(
        "chat",
        runtime_settings,
        project_id=project_id,
        secret_store=secret_store,
        session=session,
    )
    if resolved is not None:
        return _build_resolved_chat_runner(
            resolved,
            runtime_settings,
            usage_tracker=usage_tracker,
        )
    return _build_chat_runner(runtime_settings, usage_tracker=usage_tracker)


def get_rerank_provider(
    settings: Settings | None = None,
    *,
    project_id: UUID | None = None,
    secret_store: ProviderSecretStore | None = None,
    session: Session | None = None,
    usage_tracker: ProviderUsageTracker | None = None,
) -> RerankProvider:
    runtime_settings = settings or get_settings()
    resolved = _resolve_persisted_slot(
        "rerank",
        runtime_settings,
        project_id=project_id,
        secret_store=secret_store,
        session=session,
    )
    if resolved is not None:
        return _build_resolved_rerank_provider(
            resolved,
            runtime_settings,
            usage_tracker=usage_tracker,
        )
    return _build_rerank_provider(runtime_settings, usage_tracker=usage_tracker)


def get_contextualizer(
    settings: Settings | None = None,
    *,
    project_id: UUID | None = None,
    secret_store: ProviderSecretStore | None = None,
    session: Session | None = None,
) -> Contextualizer:
    runtime_settings = settings or get_settings()
    resolved = _resolve_persisted_slot(
        "contextualization",
        runtime_settings,
        project_id=project_id,
        secret_store=secret_store,
        session=session,
    )
    if resolved is None:
        return DeterministicContextualizer()
    if resolved.provider not in {"fake", "local_openai_compatible"}:
        raise ProviderConfigurationError(
            f"unsupported contextualization provider: {resolved.provider}"
        )
    return DeterministicContextualizer(model_name=resolved.model_id)


def _build_resolved_dense_embedding_provider(
    resolved: ResolvedRuntimeSlot,
    settings: Settings,
    *,
    usage_tracker: ProviderUsageTracker | None,
) -> DenseEmbeddingProvider:
    if resolved.provider == "fake":
        return FakeDenseEmbeddingProvider()
    if resolved.provider not in {"qwen", "local_openai_compatible"}:
        raise ProviderConfigurationError(
            f"unsupported embedding provider: {resolved.provider}"
        )
    if resolved.base_url is None or resolved.api_key is None:
        raise ProviderConfigurationError(
            f"incomplete_runtime_slot: {resolved.connection_id}"
        )
    return QwenDenseEmbeddingProvider(
        model_name=resolved.model_id,
        provider_name=resolved.provider,
        client=QwenHTTPEmbeddingClient(
            api_key=resolved.api_key,
            base_url=resolved.base_url,
            timeout_seconds=settings.provider_timeout_seconds,
            max_retries=settings.provider_max_retries,
            usage_tracker=(
                usage_tracker
                if usage_tracker is not None
                else InMemoryProviderUsageTracker()
            ),
            provider_name=resolved.provider,
            price_catalog=_provider_price_catalog(settings),
            budget_guard=_provider_budget_guard(settings),
        ),
    )


def _build_resolved_sparse_embedding_provider(
    resolved: ResolvedRuntimeSlot,
    settings: Settings,
    *,
    usage_tracker: ProviderUsageTracker | None,
) -> SparseEmbeddingProvider:
    if resolved.provider == "fake":
        return FakeSparseEmbeddingProvider()
    if resolved.provider != "qwen":
        raise ProviderConfigurationError(
            f"unsupported sparse embedding provider: {resolved.provider}"
        )
    if resolved.base_url is None or resolved.api_key is None:
        raise ProviderConfigurationError(
            f"incomplete_runtime_slot: {resolved.connection_id}"
        )
    return QwenSparseEmbeddingProvider(
        model_name=resolved.model_id,
        client=QwenHTTPEmbeddingClient(
            api_key=resolved.api_key,
            base_url=resolved.base_url,
            timeout_seconds=settings.provider_timeout_seconds,
            max_retries=settings.provider_max_retries,
            usage_tracker=(
                usage_tracker
                if usage_tracker is not None
                else InMemoryProviderUsageTracker()
            ),
            price_catalog=_provider_price_catalog(settings),
            budget_guard=_provider_budget_guard(settings),
        ),
    )


def _build_resolved_chat_runner(
    resolved: ResolvedRuntimeSlot,
    settings: Settings,
    *,
    usage_tracker: ProviderUsageTracker | None,
) -> ChatRunner:
    if resolved.provider == "fake":
        return RetrievalGroundedChatRunner()
    if resolved.provider not in {"qwen", "local_openai_compatible"}:
        raise ProviderConfigurationError(
            f"unsupported chat provider: {resolved.provider}"
        )
    if resolved.base_url is None or resolved.api_key is None:
        raise ProviderConfigurationError(
            f"incomplete_runtime_slot: {resolved.connection_id}"
        )
    return QwenChatRunner(
        model_name=resolved.model_id,
        provider_name=resolved.provider,
        client=QwenHTTPChatClient(
            api_key=resolved.api_key,
            base_url=resolved.base_url,
            timeout_seconds=settings.provider_timeout_seconds,
            max_retries=settings.provider_max_retries,
            usage_tracker=(
                usage_tracker
                if usage_tracker is not None
                else InMemoryProviderUsageTracker()
            ),
            provider_name=resolved.provider,
            price_catalog=_provider_price_catalog(settings),
            budget_guard=_provider_budget_guard(settings),
        ),
    )


def _build_resolved_rerank_provider(
    resolved: ResolvedRuntimeSlot,
    settings: Settings,
    *,
    usage_tracker: ProviderUsageTracker | None,
) -> RerankProvider:
    if resolved.provider == "fake":
        return FakeRerankProvider()
    if resolved.provider not in {"qwen", "local_openai_compatible"}:
        raise ProviderConfigurationError(
            f"unsupported rerank provider: {resolved.provider}"
        )
    if resolved.base_url is None or resolved.api_key is None:
        raise ProviderConfigurationError(
            f"incomplete_runtime_slot: {resolved.connection_id}"
        )
    return QwenRerankProvider(
        model_name=resolved.model_id,
        provider_name=resolved.provider,
        client=QwenHTTPRerankClient(
            api_key=resolved.api_key,
            base_url=resolved.base_url,
            timeout_seconds=settings.provider_timeout_seconds,
            max_retries=settings.provider_max_retries,
            usage_tracker=(
                usage_tracker
                if usage_tracker is not None
                else InMemoryProviderUsageTracker()
            ),
            provider_name=resolved.provider,
            price_catalog=_provider_price_catalog(settings),
            budget_guard=_provider_budget_guard(settings),
        ),
    )


def _build_embedding_provider(
    settings: Settings,
    *,
    usage_tracker: ProviderUsageTracker | None,
) -> DenseEmbeddingProvider:
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
            usage_tracker=(
                usage_tracker
                if usage_tracker is not None
                else InMemoryProviderUsageTracker()
            ),
            price_catalog=_provider_price_catalog(settings),
            budget_guard=_provider_budget_guard(settings),
        ),
    )


def _build_sparse_embedding_provider(
    settings: Settings,
    *,
    usage_tracker: ProviderUsageTracker | None,
) -> SparseEmbeddingProvider:
    if settings.provider_runtime_mode == "fake":
        if settings.sparse_embedding_provider != "fake":
            raise ProviderConfigurationError(
                f"sparse embedding provider '{settings.sparse_embedding_provider}' "
                "requires live provider runtime mode"
            )
        return FakeSparseEmbeddingProvider()

    if settings.sparse_embedding_provider != "qwen":
        raise ProviderConfigurationError(
            "unsupported sparse embedding provider: "
            f"{settings.sparse_embedding_provider}"
        )
    _require_qwen_credentials(settings)
    if (
        not settings.sparse_embedding_model
        or settings.sparse_embedding_model == "fake-sparse-embedding-v1"
    ):
        raise ProviderConfigurationError(
            "ADAPTIVE_RAG_SPARSE_EMBEDDING_MODEL must be set for qwen"
        )
    if settings.qwen_api_key is None or settings.qwen_base_url is None:
        raise ProviderConfigurationError("qwen credentials were not validated")
    return QwenSparseEmbeddingProvider(
        model_name=settings.sparse_embedding_model,
        client=QwenHTTPEmbeddingClient(
            api_key=settings.qwen_api_key.get_secret_value(),
            base_url=settings.qwen_base_url,
            timeout_seconds=settings.provider_timeout_seconds,
            max_retries=settings.provider_max_retries,
            usage_tracker=(
                usage_tracker
                if usage_tracker is not None
                else InMemoryProviderUsageTracker()
            ),
            price_catalog=_provider_price_catalog(settings),
            budget_guard=_provider_budget_guard(settings),
        ),
    )


def _build_chat_runner(
    settings: Settings,
    *,
    usage_tracker: ProviderUsageTracker | None,
) -> ChatRunner:
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
            usage_tracker=(
                usage_tracker
                if usage_tracker is not None
                else InMemoryProviderUsageTracker()
            ),
            price_catalog=_provider_price_catalog(settings),
            budget_guard=_provider_budget_guard(settings),
        ),
    )


def _build_rerank_provider(
    settings: Settings,
    *,
    usage_tracker: ProviderUsageTracker | None,
) -> RerankProvider:
    if settings.provider_runtime_mode == "fake":
        if settings.rerank_provider != "fake":
            raise ProviderConfigurationError(
                f"rerank provider '{settings.rerank_provider}' requires "
                "live provider runtime mode"
            )
        return FakeRerankProvider()

    if settings.rerank_provider != "qwen":
        raise ProviderConfigurationError(
            f"unsupported rerank provider: {settings.rerank_provider}"
        )
    _require_qwen_credentials(settings)
    if not settings.rerank_model or settings.rerank_model == "fake-rerank-v1":
        raise ProviderConfigurationError(
            "ADAPTIVE_RAG_RERANK_MODEL must be set for qwen"
        )
    if settings.qwen_api_key is None or settings.qwen_base_url is None:
        raise ProviderConfigurationError("qwen credentials were not validated")
    return QwenRerankProvider(
        model_name=settings.rerank_model,
        client=QwenHTTPRerankClient(
            api_key=settings.qwen_api_key.get_secret_value(),
            base_url=settings.qwen_base_url,
            timeout_seconds=settings.provider_timeout_seconds,
            max_retries=settings.provider_max_retries,
            usage_tracker=(
                usage_tracker
                if usage_tracker is not None
                else InMemoryProviderUsageTracker()
            ),
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
        rerank_input_price_per_million_tokens_usd=(
            settings.provider_rerank_input_price_per_million_tokens_usd
        ),
    )
