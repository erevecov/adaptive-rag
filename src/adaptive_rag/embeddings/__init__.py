"""Embeddings densos para Adaptive RAG."""

from adaptive_rag.embeddings.dense import (
    DENSE_EMBEDDING_METADATA_VERSION,
    DenseEmbeddingInput,
    DenseEmbeddingPipeline,
    DenseEmbeddingPipelineError,
    DenseEmbeddingProvider,
    DenseEmbeddingRunResult,
    EmbeddingInputBuilder,
    FakeDenseEmbeddingProvider,
)
from adaptive_rag.embeddings.qwen import (
    QwenDenseEmbeddingProvider,
    QwenEmbeddingProviderError,
    QwenHTTPEmbeddingClient,
    QwenSparseEmbeddingProvider,
)
from adaptive_rag.embeddings.sparse import (
    SPARSE_EMBEDDING_METADATA_VERSION,
    FakeSparseEmbeddingProvider,
    SparseEmbeddingPipeline,
    SparseEmbeddingPipelineError,
    SparseEmbeddingProvider,
    SparseEmbeddingRunResult,
    SparseEmbeddingVector,
    sparse_dot_product,
)

__all__ = [
    "DENSE_EMBEDDING_METADATA_VERSION",
    "DenseEmbeddingInput",
    "DenseEmbeddingPipeline",
    "DenseEmbeddingPipelineError",
    "DenseEmbeddingProvider",
    "DenseEmbeddingRunResult",
    "EmbeddingInputBuilder",
    "FakeDenseEmbeddingProvider",
    "FakeSparseEmbeddingProvider",
    "QwenDenseEmbeddingProvider",
    "QwenEmbeddingProviderError",
    "QwenHTTPEmbeddingClient",
    "QwenSparseEmbeddingProvider",
    "SPARSE_EMBEDDING_METADATA_VERSION",
    "SparseEmbeddingPipeline",
    "SparseEmbeddingPipelineError",
    "SparseEmbeddingProvider",
    "SparseEmbeddingRunResult",
    "SparseEmbeddingVector",
    "sparse_dot_product",
]
