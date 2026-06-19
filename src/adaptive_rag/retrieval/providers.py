"""Factories de providers para superficies de retrieval."""

from __future__ import annotations

from adaptive_rag.embeddings import DenseEmbeddingProvider, FakeDenseEmbeddingProvider


def get_default_dense_embedding_provider() -> DenseEmbeddingProvider:
    return FakeDenseEmbeddingProvider()

