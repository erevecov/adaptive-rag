"""Retrieval baseline para Adaptive RAG."""

from adaptive_rag.retrieval.bm25 import (
    Bm25RetrievalError,
    Bm25RetrievalResult,
    Bm25Retriever,
)
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
    "Bm25RetrievalError",
    "Bm25RetrievalResult",
    "Bm25Retriever",
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
