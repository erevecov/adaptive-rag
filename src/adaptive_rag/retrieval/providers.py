"""Factories de providers para superficies de retrieval."""

from __future__ import annotations

from adaptive_rag.embeddings import DenseEmbeddingProvider
from adaptive_rag.provider_runtime import (
    get_dense_embedding_provider as get_runtime_dense_embedding_provider,
)


def get_default_dense_embedding_provider() -> DenseEmbeddingProvider:
    return get_runtime_dense_embedding_provider()

