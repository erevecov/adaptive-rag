"""Compatibility facade for runtime provider factories."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.chat import ChatRunner
from adaptive_rag.config.settings import Settings, get_settings
from adaptive_rag.contextualization import Contextualizer
from adaptive_rag.embeddings import DenseEmbeddingProvider, SparseEmbeddingProvider
from adaptive_rag.provider_secrets import ProviderSecretStore
from adaptive_rag.provider_usage import ProviderUsageTracker
from adaptive_rag.rerank import RerankProvider
from adaptive_rag.runtime.factories import (
    get_chat_runner as _get_chat_runner,
)
from adaptive_rag.runtime.factories import (
    get_contextualizer as _get_contextualizer,
)
from adaptive_rag.runtime.factories import (
    get_dense_embedding_provider as _get_dense_embedding_provider,
)
from adaptive_rag.runtime.factories import (
    get_rerank_provider as _get_rerank_provider,
)
from adaptive_rag.runtime.factories import (
    get_sparse_embedding_provider as _get_sparse_embedding_provider,
)
from adaptive_rag.runtime.resolution import (
    ProviderConfigurationError,
    ResolvedRuntimeSlot,
)

__all__ = [
    "ProviderConfigurationError",
    "ResolvedRuntimeSlot",
    "get_chat_runner",
    "get_contextualizer",
    "get_dense_embedding_provider",
    "get_rerank_provider",
    "get_sparse_embedding_provider",
]


def get_dense_embedding_provider(
    settings: Settings | None = None,
    *,
    project_id: UUID | None = None,
    secret_store: ProviderSecretStore | None = None,
    session: Session | None = None,
    usage_tracker: ProviderUsageTracker | None = None,
) -> DenseEmbeddingProvider:
    return _get_dense_embedding_provider(
        settings or get_settings(),
        project_id=project_id,
        secret_store=secret_store,
        session=session,
        usage_tracker=usage_tracker,
    )


def get_sparse_embedding_provider(
    settings: Settings | None = None,
    *,
    project_id: UUID | None = None,
    secret_store: ProviderSecretStore | None = None,
    session: Session | None = None,
    usage_tracker: ProviderUsageTracker | None = None,
) -> SparseEmbeddingProvider:
    return _get_sparse_embedding_provider(
        settings or get_settings(),
        project_id=project_id,
        secret_store=secret_store,
        session=session,
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
    return _get_chat_runner(
        settings or get_settings(),
        project_id=project_id,
        secret_store=secret_store,
        session=session,
        usage_tracker=usage_tracker,
    )


def get_rerank_provider(
    settings: Settings | None = None,
    *,
    project_id: UUID | None = None,
    secret_store: ProviderSecretStore | None = None,
    session: Session | None = None,
    usage_tracker: ProviderUsageTracker | None = None,
) -> RerankProvider:
    return _get_rerank_provider(
        settings or get_settings(),
        project_id=project_id,
        secret_store=secret_store,
        session=session,
        usage_tracker=usage_tracker,
    )


def get_contextualizer(
    settings: Settings | None = None,
    *,
    project_id: UUID | None = None,
    secret_store: ProviderSecretStore | None = None,
    session: Session | None = None,
) -> Contextualizer:
    return _get_contextualizer(
        settings or get_settings(),
        project_id=project_id,
        secret_store=secret_store,
        session=session,
    )
