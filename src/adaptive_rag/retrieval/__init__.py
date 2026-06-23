"""Retrieval baseline para Adaptive RAG."""

from adaptive_rag.retrieval.dense import (
    DenseRetrievalCitation,
    DenseRetrievalError,
    DenseRetrievalFilters,
    DenseRetrievalResult,
    DenseRetriever,
)
from adaptive_rag.retrieval.lexical import (
    LexicalRetrievalError,
    LexicalRetrievalResult,
    LexicalRetriever,
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
from adaptive_rag.retrieval.sparse import (
    SparseRetrievalError,
    SparseRetrievalResult,
    SparseRetriever,
)

__all__ = [
    "DenseRetriever",
    "DenseRetrievalCitation",
    "DenseRetrievalError",
    "DenseRetrievalFilters",
    "DenseRetrievalResult",
    "LexicalRetrievalError",
    "LexicalRetrievalResult",
    "LexicalRetriever",
    "RetrievalMetadataFilter",
    "RetrievalRerankOptions",
    "RetrievalSearchRequest",
    "RetrievalSearchResult",
    "RetrievalService",
    "RetrievalServiceError",
    "RetrievalStrategy",
    "SparseRetrievalError",
    "SparseRetrievalResult",
    "SparseRetriever",
]
