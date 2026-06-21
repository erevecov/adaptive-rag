"""Dependencias compartidas por comandos CLI."""

from __future__ import annotations

from dataclasses import dataclass

from adaptive_rag.chat import ChatRunner
from adaptive_rag.config.settings import get_settings
from adaptive_rag.embeddings import DenseEmbeddingProvider
from adaptive_rag.evals import (
    EvalRunOptions,
    validate_hosted_eval_credentials,
)
from adaptive_rag.provider_runtime import (
    get_chat_runner,
    get_dense_embedding_provider,
    get_rerank_provider,
)
from adaptive_rag.provider_usage import InMemoryProviderUsageTracker
from adaptive_rag.rerank import RerankProvider
from adaptive_rag.retrieval.providers import get_default_dense_embedding_provider


@dataclass(frozen=True, slots=True)
class CliHostedEvalRuntime:
    provider: DenseEmbeddingProvider
    chat_runner: ChatRunner
    reranker: RerankProvider | None
    usage_tracker: InMemoryProviderUsageTracker
    options: EvalRunOptions


def get_cli_dense_embedding_provider() -> DenseEmbeddingProvider:
    return get_default_dense_embedding_provider()


def get_cli_chat_runner(
    *,
    usage_tracker: InMemoryProviderUsageTracker | None = None,
) -> ChatRunner:
    return get_chat_runner(usage_tracker=usage_tracker)


def get_cli_rerank_provider() -> RerankProvider:
    return get_rerank_provider()


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
