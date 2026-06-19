"""Retrieval baseline para Adaptive RAG."""

from adaptive_rag.retrieval.dense import (
    DenseRetrievalCitation,
    DenseRetrievalError,
    DenseRetrievalFilters,
    DenseRetrievalResult,
    DenseRetriever,
)

__all__ = [
    "DenseRetriever",
    "DenseRetrievalCitation",
    "DenseRetrievalError",
    "DenseRetrievalFilters",
    "DenseRetrievalResult",
]
