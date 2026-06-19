"""FastAPI dependencies para superficies HTTP."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from adaptive_rag.db.session import session_scope
from adaptive_rag.embeddings import DenseEmbeddingProvider, FakeDenseEmbeddingProvider
from adaptive_rag.retrieval import RetrievalService


def get_session() -> Iterator[Session]:
    with session_scope() as session:
        yield session


def get_dense_embedding_provider() -> DenseEmbeddingProvider:
    return FakeDenseEmbeddingProvider()


def get_retrieval_service(
    session: Annotated[Session, Depends(get_session)],
    provider: Annotated[
        DenseEmbeddingProvider,
        Depends(get_dense_embedding_provider),
    ],
) -> RetrievalService:
    return RetrievalService(session, provider=provider)

