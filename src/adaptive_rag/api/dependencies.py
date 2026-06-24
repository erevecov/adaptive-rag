"""FastAPI dependencies para superficies HTTP."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from inspect import Parameter, signature
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.params import Depends as DependsMarker
from sqlalchemy.orm import Session

from adaptive_rag.chat import ChatRunner, ChatService, SqlAlchemyChatAuditWriter
from adaptive_rag.config.settings import get_settings
from adaptive_rag.db.repositories import ChatAuditRepository, ProviderUsageRepository
from adaptive_rag.db.session import session_scope
from adaptive_rag.embeddings import DenseEmbeddingProvider, SparseEmbeddingProvider
from adaptive_rag.graph import GraphRetriever, get_graph_store
from adaptive_rag.provider_models import HTTPProviderModelLister, ProviderModelLister
from adaptive_rag.provider_runtime import get_chat_runner as get_runtime_chat_runner
from adaptive_rag.provider_runtime import (
    get_rerank_provider as get_runtime_rerank_provider,
)
from adaptive_rag.provider_secrets import ProviderSecretKeyError, ProviderSecretStore
from adaptive_rag.provider_usage import InMemoryProviderUsageTracker
from adaptive_rag.rerank import RerankProvider
from adaptive_rag.retrieval import RetrievalService
from adaptive_rag.retrieval.providers import (
    get_default_dense_embedding_provider,
    get_default_sparse_embedding_provider,
)

RerankProviderFactory = Callable[[], RerankProvider]
SparseEmbeddingProviderFactory = Callable[[], SparseEmbeddingProvider]


def get_session() -> Iterator[Session]:
    with session_scope() as session:
        yield session


def get_graph_retriever() -> GraphRetriever | None:
    graph_store = get_graph_store()
    if hasattr(graph_store, "expand_project_chunks"):
        return cast(GraphRetriever, graph_store)
    return None


def get_provider_usage_tracker() -> InMemoryProviderUsageTracker:
    return InMemoryProviderUsageTracker()


def get_provider_secret_store() -> ProviderSecretStore:
    try:
        return ProviderSecretStore.from_settings()
    except ProviderSecretKeyError as exc:
        code = (
            "provider_secret_key_missing"
            if "is required" in str(exc)
            else "provider_secret_key_invalid"
        )
        raise HTTPException(
            status_code=422,
            detail={"code": code, "message": str(exc)},
        ) from exc


def get_provider_model_lister() -> ProviderModelLister:
    return HTTPProviderModelLister(
        timeout_seconds=get_settings().provider_timeout_seconds,
    )


_SESSION_DEPENDENCY = Depends(get_session)
_DENSE_PROVIDER_USAGE_TRACKER_DEPENDENCY = Depends(get_provider_usage_tracker)
_SPARSE_PROVIDER_USAGE_TRACKER_DEPENDENCY = Depends(get_provider_usage_tracker)
_RERANK_PROVIDER_USAGE_TRACKER_DEPENDENCY = Depends(get_provider_usage_tracker)
_CHAT_RUNNER_USAGE_TRACKER_DEPENDENCY = Depends(get_provider_usage_tracker)


def _call_with_supported_kwargs(factory: Callable[..., Any], **kwargs: object) -> Any:
    parameters = signature(factory).parameters
    if any(
        parameter.kind is Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    ):
        return factory(**kwargs)
    supported_kwargs = {
        name: value for name, value in kwargs.items() if name in parameters
    }
    return factory(**supported_kwargs)


def get_rerank_provider_factory(
    project_id: UUID | None = None,
    session: Session | DependsMarker = _SESSION_DEPENDENCY,
    usage_tracker: InMemoryProviderUsageTracker | DependsMarker = (
        _RERANK_PROVIDER_USAGE_TRACKER_DEPENDENCY
    ),
) -> RerankProviderFactory:
    active_session = None if isinstance(session, DependsMarker) else session
    active_usage_tracker = (
        get_provider_usage_tracker()
        if isinstance(usage_tracker, DependsMarker)
        else usage_tracker
    )

    def build() -> RerankProvider:
        return cast(
            RerankProvider,
            _call_with_supported_kwargs(
                get_runtime_rerank_provider,
                project_id=project_id,
                session=active_session,
                usage_tracker=active_usage_tracker,
            ),
        )

    return build


def get_sparse_embedding_provider_factory(
    project_id: UUID | None = None,
    session: Session | DependsMarker = _SESSION_DEPENDENCY,
    usage_tracker: InMemoryProviderUsageTracker | DependsMarker = (
        _SPARSE_PROVIDER_USAGE_TRACKER_DEPENDENCY
    ),
) -> SparseEmbeddingProviderFactory:
    active_session = None if isinstance(session, DependsMarker) else session
    active_usage_tracker = (
        get_provider_usage_tracker()
        if isinstance(usage_tracker, DependsMarker)
        else usage_tracker
    )

    def build() -> SparseEmbeddingProvider:
        return cast(
            SparseEmbeddingProvider,
            _call_with_supported_kwargs(
                get_default_sparse_embedding_provider,
                project_id=project_id,
                session=active_session,
                usage_tracker=active_usage_tracker,
            ),
        )

    return build


def get_dense_embedding_provider(
    project_id: UUID | None = None,
    session: Session | DependsMarker = _SESSION_DEPENDENCY,
    usage_tracker: InMemoryProviderUsageTracker | DependsMarker = (
        _DENSE_PROVIDER_USAGE_TRACKER_DEPENDENCY
    ),
) -> DenseEmbeddingProvider:
    active_session = None if isinstance(session, DependsMarker) else session
    active_usage_tracker = (
        get_provider_usage_tracker()
        if isinstance(usage_tracker, DependsMarker)
        else usage_tracker
    )
    return cast(
        DenseEmbeddingProvider,
        _call_with_supported_kwargs(
            get_default_dense_embedding_provider,
            project_id=project_id,
            session=active_session,
            usage_tracker=active_usage_tracker,
        ),
    )


def get_sparse_embedding_provider(
    project_id: UUID | None = None,
    session: Session | DependsMarker = _SESSION_DEPENDENCY,
    usage_tracker: InMemoryProviderUsageTracker | DependsMarker = (
        _SPARSE_PROVIDER_USAGE_TRACKER_DEPENDENCY
    ),
) -> SparseEmbeddingProvider:
    active_session = None if isinstance(session, DependsMarker) else session
    active_usage_tracker = (
        get_provider_usage_tracker()
        if isinstance(usage_tracker, DependsMarker)
        else usage_tracker
    )
    return cast(
        SparseEmbeddingProvider,
        _call_with_supported_kwargs(
            get_default_sparse_embedding_provider,
            project_id=project_id,
            session=active_session,
            usage_tracker=active_usage_tracker,
        ),
    )


def get_retrieval_service(
    session: Annotated[Session, Depends(get_session)],
    provider: Annotated[
        DenseEmbeddingProvider,
        Depends(get_dense_embedding_provider),
    ],
) -> RetrievalService:
    return RetrievalService(session, provider=provider)


def get_chat_audit_writer(
    session: Annotated[Session, Depends(get_session)],
) -> SqlAlchemyChatAuditWriter:
    return SqlAlchemyChatAuditWriter(
        session=session,
        chat_audit_repository=ChatAuditRepository(session),
        provider_usage_repository=ProviderUsageRepository(session),
    )


def get_chat_runner(
    project_id: UUID | None = None,
    session: Session | DependsMarker = _SESSION_DEPENDENCY,
    usage_tracker: InMemoryProviderUsageTracker | DependsMarker = (
        _CHAT_RUNNER_USAGE_TRACKER_DEPENDENCY
    ),
) -> ChatRunner:
    active_session = None if isinstance(session, DependsMarker) else session
    active_usage_tracker = (
        get_provider_usage_tracker()
        if isinstance(usage_tracker, DependsMarker)
        else usage_tracker
    )
    return cast(
        ChatRunner,
        _call_with_supported_kwargs(
            get_runtime_chat_runner,
            project_id=project_id,
            session=active_session,
            usage_tracker=active_usage_tracker,
        ),
    )


def get_chat_service(
    retrieval_service: Annotated[
        RetrievalService,
        Depends(get_retrieval_service),
    ],
    runner: Annotated[
        ChatRunner,
        Depends(get_chat_runner),
    ],
    audit_writer: Annotated[
        SqlAlchemyChatAuditWriter,
        Depends(get_chat_audit_writer),
    ],
    usage_tracker: Annotated[
        InMemoryProviderUsageTracker,
        Depends(get_provider_usage_tracker),
    ],
) -> ChatService:
    return ChatService(
        runner=runner,
        retrieval_service=retrieval_service,
        audit_writer=audit_writer,
        provider_usage_records=lambda: usage_tracker.records,
    )

