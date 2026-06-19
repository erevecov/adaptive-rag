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
    RetrievalSearchRequest,
    RetrievalSearchResult,
    RetrievalService,
    RetrievalServiceError,
)

__all__ = [
    "DenseRetriever",
    "DenseRetrievalCitation",
    "DenseRetrievalError",
    "DenseRetrievalFilters",
    "DenseRetrievalResult",
    "RetrievalMetadataFilter",
    "RetrievalSearchRequest",
    "RetrievalSearchResult",
    "RetrievalService",
    "RetrievalServiceError",
]
