"""Factories de providers para superficies de retrieval."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.embeddings import DenseEmbeddingProvider, SparseEmbeddingProvider
from adaptive_rag.provider_runtime import (
    get_dense_embedding_provider as get_runtime_dense_embedding_provider,
)
from adaptive_rag.provider_runtime import (
    get_sparse_embedding_provider as get_runtime_sparse_embedding_provider,
)
from adaptive_rag.provider_usage import ProviderUsageTracker


def get_default_dense_embedding_provider(
    *,
    project_id: UUID | None = None,
    session: Session | None = None,
    usage_tracker: ProviderUsageTracker | None = None,
) -> DenseEmbeddingProvider:
    return get_runtime_dense_embedding_provider(
        project_id=project_id,
        session=session,
        usage_tracker=usage_tracker,
    )


def get_default_sparse_embedding_provider(
    *,
    project_id: UUID | None = None,
    session: Session | None = None,
    usage_tracker: ProviderUsageTracker | None = None,
) -> SparseEmbeddingProvider:
    return get_runtime_sparse_embedding_provider(
        project_id=project_id,
        session=session,
        usage_tracker=usage_tracker,
    )

