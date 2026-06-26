"""Configuracion y factories del runtime de providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.chat import ChatRunner, QwenChatRunner, RetrievalGroundedChatRunner
from adaptive_rag.chat.qwen import QwenHTTPChatClient
from adaptive_rag.config.settings import Settings, get_settings
from adaptive_rag.contextualization import Contextualizer, DeterministicContextualizer
from adaptive_rag.db.models import ProviderConnection, ProviderSecret
from adaptive_rag.db.repositories import (
    EffectiveChatModel,
    EffectiveRuntimeSlot,
    ProjectRuntimeSettingsRepository,
    RuntimeSettingsRepository,
)
from adaptive_rag.embeddings import (
    DenseEmbeddingProvider,
    FakeDenseEmbeddingProvider,
    FakeSparseEmbeddingProvider,
    QwenDenseEmbeddingProvider,
    QwenHTTPEmbeddingClient,
    QwenSparseEmbeddingProvider,
    SparseEmbeddingProvider,
)
from adaptive_rag.provider_secrets import (
    ProviderSecretDecryptError,
    ProviderSecretStore,
)
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


class ProviderConfigurationError(ValueError):
    """Error estable de configuracion para providers live."""


@dataclass(frozen=True, slots=True)
class ResolvedRuntimeSlot:
    """Runtime slot resolved from persisted settings."""

    slot: str
    provider: str
    connection_id: str
    model_id: str
    base_url: str | None
    parameters: dict[str, Any] | None
    api_key: str | None = field(repr=False)


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


def _resolve_persisted_slot(
    slot: str,
    settings: Settings,
    *,
    project_id: UUID | None,
    secret_store: ProviderSecretStore | None,
    session: Session | None,
) -> ResolvedRuntimeSlot | None:
    if session is None:
        return None

    if project_id is None:
        runtime_settings_repository = RuntimeSettingsRepository(session)
        if slot == "chat":
            chat_model = _global_chat_model(
                runtime_settings_repository.list_chat_models()
            )
            if chat_model is not None:
                connection_id = chat_model.connection_id
                model_id = chat_model.model_id
                parameters = chat_model.parameters_json
            else:
                slot_default = runtime_settings_repository.get_slot_default(slot)
                if slot_default is None:
                    return None
                connection_id = slot_default.connection_id
                model_id = slot_default.model_id
                parameters = slot_default.parameters_json
        else:
            slot_default = runtime_settings_repository.get_slot_default(slot)
            if slot_default is None:
                return None
            connection_id = slot_default.connection_id
            model_id = slot_default.model_id
            parameters = slot_default.parameters_json
    else:
        try:
            runtime_settings = ProjectRuntimeSettingsRepository(
                session
            ).get_project_runtime_settings(project_id)
        except ValueError as exc:
            raise ProviderConfigurationError(str(exc)) from exc

        effective_chat_model = (
            _effective_chat_model(runtime_settings.chat_models)
            if slot == "chat"
            else None
        )
        if effective_chat_model is not None:
            connection_id = effective_chat_model.connection_id
            model_id = effective_chat_model.model_id
            parameters = effective_chat_model.parameters_json
        else:
            effective_slot = _effective_slot(runtime_settings.slots, slot)
            if effective_slot is None:
                return None
            connection_id = effective_slot.connection_id
            model_id = effective_slot.model_id
            parameters = effective_slot.parameters_json

    connection = session.get(ProviderConnection, connection_id)
    if connection is None:
        raise ProviderConfigurationError(f"connection_not_found: {connection_id}")
    return _resolved_slot(
        slot=slot,
        model_id=model_id,
        parameters=parameters,
        connection=connection,
        secret_store=secret_store,
        session=session,
        settings=settings,
    )


def _effective_slot(
    slots: list[EffectiveRuntimeSlot],
    slot: str,
) -> EffectiveRuntimeSlot | None:
    for item in slots:
        if item.slot == slot:
            return item
    return None


def _global_chat_model(chat_models: list[Any]) -> Any | None:
    for model in chat_models:
        if model.is_default:
            return model
    return None


def _effective_chat_model(
    chat_models: list[EffectiveChatModel],
) -> EffectiveChatModel | None:
    for model in chat_models:
        if model.is_default:
            return model
    return None


def _resolved_slot(
    *,
    slot: str,
    model_id: str,
    parameters: dict[str, Any] | None,
    connection: ProviderConnection,
    secret_store: ProviderSecretStore | None,
    session: Session,
    settings: Settings,
) -> ResolvedRuntimeSlot:
    api_key = _api_key_for_connection(
        connection,
        secret_store=secret_store,
        session=session,
        settings=settings,
    )
    base_url = _base_url_for_connection(connection, settings)
    return ResolvedRuntimeSlot(
        slot=slot,
        provider=connection.provider,
        connection_id=connection.connection_id,
        model_id=model_id,
        base_url=base_url,
        parameters=parameters,
        api_key=api_key,
    )


def _api_key_for_connection(
    connection: ProviderConnection,
    *,
    secret_store: ProviderSecretStore | None,
    session: Session,
    settings: Settings,
) -> str | None:
    if connection.provider == "fake":
        return None

    secret = session.get(ProviderSecret, (connection.connection_id, "api_key"))
    if secret is not None:
        active_store = secret_store or ProviderSecretStore.from_settings(settings)
        try:
            return active_store.decrypt(secret.encrypted_value)
        except ProviderSecretDecryptError as exc:
            raise ProviderConfigurationError(
                f"provider_secret_decrypt_failed: {connection.connection_id} api_key"
            ) from exc

    if connection.provider == "qwen" and settings.qwen_api_key is not None:
        return settings.qwen_api_key.get_secret_value()
    if connection.provider == "local_openai_compatible":
        return ""
    raise ProviderConfigurationError(
        f"missing_provider_secret: {connection.connection_id} api_key is required"
    )


def _base_url_for_connection(
    connection: ProviderConnection,
    settings: Settings,
) -> str | None:
    if connection.provider == "fake":
        return None
    if connection.base_url:
        return connection.base_url
    if connection.provider == "qwen" and settings.qwen_base_url:
        return settings.qwen_base_url
    raise ProviderConfigurationError(
        f"missing_provider_base_url: {connection.connection_id} base_url is required"
    )


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
