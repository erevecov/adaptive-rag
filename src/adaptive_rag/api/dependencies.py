"""FastAPI dependencies para superficies HTTP."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from adaptive_rag.chat import ChatRunner, ChatService
from adaptive_rag.db.session import session_scope
from adaptive_rag.embeddings import DenseEmbeddingProvider
from adaptive_rag.provider_runtime import get_chat_runner as get_runtime_chat_runner
from adaptive_rag.retrieval import RetrievalService
from adaptive_rag.retrieval.providers import get_default_dense_embedding_provider


def get_session() -> Iterator[Session]:
    with session_scope() as session:
        yield session


def get_dense_embedding_provider() -> DenseEmbeddingProvider:
    return get_default_dense_embedding_provider()


def get_retrieval_service(
    session: Annotated[Session, Depends(get_session)],
    provider: Annotated[
        DenseEmbeddingProvider,
        Depends(get_dense_embedding_provider),
    ],
) -> RetrievalService:
    return RetrievalService(session, provider=provider)


def get_chat_runner() -> ChatRunner:
    return get_runtime_chat_runner()


def get_chat_service(
    retrieval_service: Annotated[
        RetrievalService,
        Depends(get_retrieval_service),
    ],
    runner: Annotated[
        ChatRunner,
        Depends(get_chat_runner),
    ],
) -> ChatService:
    return ChatService(
        runner=runner,
        retrieval_service=retrieval_service,
    )

