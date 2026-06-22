"""Retrieval baseline para Adaptive RAG."""

from adaptive_rag.retrieval.dense import (
    DenseRetrievalCitation,
    DenseRetrievalError,
    DenseRetrievalFilters,
    DenseRetrievalResult,
    DenseRetriever,
)
from adaptive_rag.retrieval.service import (
    RetrievalMetadataFilter,
    RetrievalRerankOptions,
    RetrievalSearchRequest,
    RetrievalSearchResult,
    RetrievalService,
    RetrievalServiceError,
    RetrievalStrategy,
)

__all__ = [
    "DenseRetriever",
    "DenseRetrievalCitation",
    "DenseRetrievalError",
    "DenseRetrievalFilters",
    "DenseRetrievalResult",
    "RetrievalMetadataFilter",
    "RetrievalRerankOptions",
    "RetrievalSearchRequest",
    "RetrievalSearchResult",
    "RetrievalService",
    "RetrievalServiceError",
    "RetrievalStrategy",
]
