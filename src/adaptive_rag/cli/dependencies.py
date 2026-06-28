"""Dependencias compartidas por comandos CLI."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from inspect import signature
from typing import Any, cast
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.chat import ChatRunner
from adaptive_rag.config.settings import get_settings
from adaptive_rag.embeddings import DenseEmbeddingProvider, SparseEmbeddingProvider
from adaptive_rag.evals import (
    EvalRunOptions,
    validate_hosted_eval_credentials,
)
from adaptive_rag.graph import GraphRetriever, GraphStore, get_graph_store
from adaptive_rag.provider_runtime import (
    get_chat_runner,
    get_dense_embedding_provider,
    get_rerank_provider,
    get_sparse_embedding_provider,
)
from adaptive_rag.provider_usage import InMemoryProviderUsageTracker
from adaptive_rag.rerank import RerankProvider
from adaptive_rag.retrieval.providers import (
    get_default_dense_embedding_provider,
    get_default_sparse_embedding_provider,
)


@dataclass(frozen=True, slots=True)
class CliHostedEvalRuntime:
    provider: DenseEmbeddingProvider
    sparse_provider: SparseEmbeddingProvider
    chat_runner: ChatRunner
    reranker: RerankProvider | None
    usage_tracker: InMemoryProviderUsageTracker
    options: EvalRunOptions


def get_cli_dense_embedding_provider(
    *,
    project_id: UUID | None = None,
    session: Session | None = None,
    usage_tracker: InMemoryProviderUsageTracker | None = None,
) -> DenseEmbeddingProvider:
    kwargs = _runtime_factory_kwargs(
        get_default_dense_embedding_provider,
        project_id=project_id,
        session=session,
        usage_tracker=usage_tracker,
    )
    return cast(
        DenseEmbeddingProvider,
        cast(Any, get_default_dense_embedding_provider)(**kwargs),
    )


def get_cli_sparse_embedding_provider(
    *,
    project_id: UUID | None = None,
    session: Session | None = None,
    usage_tracker: InMemoryProviderUsageTracker | None = None,
) -> SparseEmbeddingProvider:
    kwargs = _runtime_factory_kwargs(
        get_default_sparse_embedding_provider,
        project_id=project_id,
        session=session,
        usage_tracker=usage_tracker,
    )
    return cast(
        SparseEmbeddingProvider,
        cast(Any, get_default_sparse_embedding_provider)(**kwargs),
    )


def get_cli_chat_runner(
    *,
    project_id: UUID | None = None,
    session: Session | None = None,
    usage_tracker: InMemoryProviderUsageTracker | None = None,
) -> ChatRunner:
    return get_chat_runner(
        project_id=project_id,
        session=session,
        usage_tracker=usage_tracker,
    )


def get_cli_rerank_provider(
    *,
    project_id: UUID | None = None,
    session: Session | None = None,
    usage_tracker: InMemoryProviderUsageTracker | None = None,
) -> RerankProvider:
    return get_rerank_provider(
        project_id=project_id,
        session=session,
        usage_tracker=usage_tracker,
    )


def _runtime_factory_kwargs(
    factory: Callable[..., object],
    *,
    project_id: UUID | None,
    session: Session | None,
    usage_tracker: InMemoryProviderUsageTracker | None,
) -> dict[str, object]:
    parameters = signature(factory).parameters
    kwargs: dict[str, object] = {}
    if "project_id" in parameters:
        kwargs["project_id"] = project_id
    if "session" in parameters:
        kwargs["session"] = session
    if "usage_tracker" in parameters:
        kwargs["usage_tracker"] = usage_tracker
    return kwargs


def get_cli_graph_store() -> GraphStore:
    return get_graph_store()


def get_cli_graph_retriever() -> GraphRetriever | None:
    graph_store = get_cli_graph_store()
    if hasattr(graph_store, "expand_project_chunks"):
        return cast(GraphRetriever, graph_store)
    return None


def get_cli_hosted_eval_runtime(
    *,
    provider_name: str,
    max_cost_usd: float | None,
    include_reranker: bool = False,
) -> CliHostedEvalRuntime:
    settings = get_settings().model_copy(
        update={
            "provider_runtime_mode": "live",
            "embedding_provider": provider_name,
            "sparse_embedding_provider": provider_name,
            "chat_provider": provider_name,
            **({"rerank_provider": provider_name} if include_reranker else {}),
            "provider_max_cost_usd": max_cost_usd,
        }
    )
    options = EvalRunOptions(
        mode="hosted",
        provider=provider_name,
        max_cost_usd=max_cost_usd,
    )
    validate_hosted_eval_credentials(
        options,
        qwen_api_key=settings.qwen_api_key,
        qwen_base_url=settings.qwen_base_url,
    )
    usage_tracker = InMemoryProviderUsageTracker()
    return CliHostedEvalRuntime(
        provider=get_dense_embedding_provider(
            settings,
            usage_tracker=usage_tracker,
        ),
        sparse_provider=get_sparse_embedding_provider(
            settings,
            usage_tracker=usage_tracker,
        ),
        chat_runner=get_chat_runner(
            settings,
            usage_tracker=usage_tracker,
        ),
        reranker=(
            get_rerank_provider(settings, usage_tracker=usage_tracker)
            if include_reranker
            else None
        ),
        usage_tracker=usage_tracker,
        options=options,
    )
