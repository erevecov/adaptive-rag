"""Factories de providers para superficies de retrieval."""

from __future__ import annotations

from adaptive_rag.embeddings import DenseEmbeddingProvider
from adaptive_rag.provider_runtime import (
    get_dense_embedding_provider as get_runtime_dense_embedding_provider,
)
from adaptive_rag.provider_usage import ProviderUsageTracker


def get_default_dense_embedding_provider(
    *,
    usage_tracker: ProviderUsageTracker | None = None,
) -> DenseEmbeddingProvider:
    return get_runtime_dense_embedding_provider(usage_tracker=usage_tracker)

