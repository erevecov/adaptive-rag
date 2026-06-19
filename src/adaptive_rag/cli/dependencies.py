"""Dependencias compartidas por comandos CLI."""

from __future__ import annotations

from adaptive_rag.chat import ChatRunner
from adaptive_rag.embeddings import DenseEmbeddingProvider
from adaptive_rag.provider_runtime import get_chat_runner
from adaptive_rag.retrieval.providers import get_default_dense_embedding_provider


def get_cli_dense_embedding_provider() -> DenseEmbeddingProvider:
    return get_default_dense_embedding_provider()


def get_cli_chat_runner() -> ChatRunner:
    return get_chat_runner()
