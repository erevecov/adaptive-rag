"""FastAPI dependencies para superficies HTTP."""

from __future__ import annotations

import hmac
from collections.abc import Callable, Iterator, Sequence
from datetime import timedelta
from inspect import Parameter, signature
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from fastapi.params import Depends as DependsMarker
from sqlalchemy import Connection
from sqlalchemy.orm import Session

from adaptive_rag.api.errors import raise_api_error
from adaptive_rag.auth import (
    CurrentPrincipal,
    get_workspace_role,
    hash_access_token,
    role_meets,
)
from adaptive_rag.chat import ChatRunner, ChatService, SqlAlchemyChatAuditWriter
from adaptive_rag.chat.attachments import ChatAttachmentContext
from adaptive_rag.chat.knowledge import SqlAlchemyKnowledgeProposalSubmitter
from adaptive_rag.config.settings import get_settings
from adaptive_rag.db.models import Workspace
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.repositories import (
    ChatAuditRepository,
    ProviderUsageRepository,
    WorkspaceRepository,
)
from adaptive_rag.db.repositories.users import HumanAuthRepository, UserRepository
from adaptive_rag.db.session import create_session_factory, session_scope
from adaptive_rag.embeddings import DenseEmbeddingProvider, SparseEmbeddingProvider
from adaptive_rag.graph import GraphRetriever, get_graph_store
from adaptive_rag.jobs.handlers import build_ingestion_registry
from adaptive_rag.jobs.registry import JobRegistry
from adaptive_rag.provider_models import HTTPProviderModelLister, ProviderModelLister
from adaptive_rag.provider_runtime import get_chat_runner as get_runtime_chat_runner
from adaptive_rag.provider_runtime import (
    get_rerank_provider as get_runtime_rerank_provider,
)
from adaptive_rag.provider_runtime import (
    get_vision_chat_runner as get_runtime_vision_chat_runner,
)
from adaptive_rag.provider_secrets import ProviderSecretKeyError, ProviderSecretStore
from adaptive_rag.provider_usage import InMemoryProviderUsageTracker
from adaptive_rag.rerank import RerankProvider
from adaptive_rag.retrieval import (
    RetrievalSearchRequest,
    RetrievalSearchResult,
    RetrievalService,
)
from adaptive_rag.retrieval.providers import (
    get_default_dense_embedding_provider,
    get_default_sparse_embedding_provider,
)
from adaptive_rag.security.human_auth import hash_opaque_secret

SESSION_COOKIE_NAME = "adaptive_rag_session"
SAFE_HTTP_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
PASSWORD_CHANGE_PATHS = frozenset(
    {"/auth/me", "/auth/csrf", "/auth/change-password", "/auth/logout"}
)

RerankProviderFactory = Callable[[], RerankProvider]
SparseEmbeddingProviderFactory = Callable[[], SparseEmbeddingProvider]


def get_session() -> Iterator[Session]:
    with session_scope() as session:
        yield session


def get_job_registry(
    session: Annotated[Session, Depends(get_session)],
) -> JobRegistry:
    bind = session.get_bind()
    engine = bind.engine if isinstance(bind, Connection) else bind
    return build_ingestion_registry(session_factory=create_session_factory(engine))


def get_current_user(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentPrincipal:
    raw_session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if raw_session_token:
        settings = get_settings()
        auth_repo = HumanAuthRepository(session)
        human_session = auth_repo.get_active_session(
            token_hash=hash_opaque_secret(raw_session_token),
            now=utc_now(),
            idle_timeout=timedelta(hours=settings.auth_session_idle_hours),
        )
        if human_session is None:
            session.commit()
            raise_api_error(401, "authentication_required")
        user = UserRepository(session).get_user(human_session.user_id)
        if user is None:
            raise_api_error(401, "authentication_required")
        credential = auth_repo.get_credential(user.id)
        current = CurrentPrincipal(
            user=user,
            auth_method="session",
            session_id=human_session.id,
            csrf_token_hash=human_session.csrf_token_hash,
            must_change_password=(
                credential.must_change_password if credential is not None else False
            ),
        )
        _enforce_cookie_request_security(request, current)
        session.commit()
        if (
            current.must_change_password
            and request.url.path not in PASSWORD_CHANGE_PATHS
        ):
            raise_api_error(403, "password_change_required")
        return current

    if authorization is None or authorization.strip() == "":
        raise_api_error(401, "authentication_required")

    raw_token = _parse_bearer_token(authorization)
    user = UserRepository(session).get_user_by_token_hash(hash_access_token(raw_token))
    if user is None or not user.is_active:
        raise_api_error(401, "invalid_access_token")
    return CurrentPrincipal(
        user=user,
        auth_method="bearer",
        must_change_password=False,
    )


def require_superadmin(current: CurrentPrincipal) -> None:
    if not current.is_superadmin:
        raise_api_error(403, "superadmin_required")


def get_superadmin_user(
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> CurrentPrincipal:
    require_superadmin(current)
    return current


def get_workspace_access(
    workspace_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> tuple[Workspace, str]:
    # WorkspaceRepository.get omits soft-deleted rows (deleted_at set).
    workspace = WorkspaceRepository(session).get(workspace_id)
    if workspace is None:
        raise_api_error(404, "workspace_not_found")
    role = get_workspace_role(session, principal=current, workspace_id=workspace_id)
    if role is None:
        raise_api_error(403, "workspace_access_required")
    return workspace, role


def get_workspace_contributor_access(
    access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
) -> tuple[Workspace, str]:
    if not role_meets(access[1], "contributor"):
        raise_api_error(403, "workspace_contributor_required")
    return access


def get_workspace_admin_access(
    access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
) -> tuple[Workspace, str]:
    if not role_meets(access[1], "admin"):
        raise_api_error(403, "workspace_admin_required")
    return access


def _parse_bearer_token(authorization: str) -> str:
    scheme, separator, token = authorization.partition(" ")
    if separator == "" or scheme.lower() != "bearer" or token.strip() == "":
        raise_api_error(401, "invalid_access_token")
    return token.strip()


def _enforce_cookie_request_security(
    request: Request, current: CurrentPrincipal
) -> None:
    if request.method in SAFE_HTTP_METHODS:
        return
    origin = request.headers.get("origin")
    csrf_token = request.headers.get("x-csrf-token")
    settings = get_settings()
    if origin not in settings.cors_allowed_origins:
        raise_api_error(403, "csrf_failed")
    if (
        csrf_token is None
        or current.csrf_token_hash is None
        or not hmac.compare_digest(
            hash_opaque_secret(csrf_token), current.csrf_token_hash
        )
    ):
        raise_api_error(403, "csrf_failed")


def get_graph_retriever() -> GraphRetriever | None:
    graph_store = get_graph_store()
    if hasattr(graph_store, "expand_workspace_chunks"):
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
_VISION_CHAT_RUNNER_USAGE_TRACKER_DEPENDENCY = Depends(get_provider_usage_tracker)


def _call_with_supported_kwargs(factory: Callable[..., Any], **kwargs: object) -> Any:
    parameters = signature(factory).parameters
    if any(
        parameter.kind is Parameter.VAR_KEYWORD for parameter in parameters.values()
    ):
        return factory(**kwargs)
    supported_kwargs = {
        name: value for name, value in kwargs.items() if name in parameters
    }
    return factory(**supported_kwargs)


def get_rerank_provider_factory(
    workspace_id: UUID | None = None,
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
                workspace_id=workspace_id,
                session=active_session,
                usage_tracker=active_usage_tracker,
            ),
        )

    return build


def get_sparse_embedding_provider_factory(
    workspace_id: UUID | None = None,
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
                workspace_id=workspace_id,
                session=active_session,
                usage_tracker=active_usage_tracker,
            ),
        )

    return build


def get_dense_embedding_provider(
    workspace_id: UUID | None = None,
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
            workspace_id=workspace_id,
            session=active_session,
            usage_tracker=active_usage_tracker,
        ),
    )


def get_sparse_embedding_provider(
    workspace_id: UUID | None = None,
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
            workspace_id=workspace_id,
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
    sparse_provider_factory: Annotated[
        SparseEmbeddingProviderFactory,
        Depends(get_sparse_embedding_provider_factory),
    ],
) -> RetrievalService:
    return RetrievalService(
        session,
        provider=provider,
        sparse_provider=sparse_provider_factory(),
    )


class LazyChatRetrievalSearcher:
    """Builds optional retrieval dependencies only when the chat tool is used."""

    def __init__(
        self,
        *,
        session: Session,
        provider: DenseEmbeddingProvider,
        sparse_provider_factory: SparseEmbeddingProviderFactory,
        rerank_provider_factory: RerankProviderFactory,
        graph_retriever: GraphRetriever | None,
    ) -> None:
        self._session = session
        self._provider = provider
        self._sparse_provider_factory = sparse_provider_factory
        self._rerank_provider_factory = rerank_provider_factory
        self._graph_retriever = graph_retriever

    def search(
        self,
        request: RetrievalSearchRequest,
    ) -> list[RetrievalSearchResult]:
        service = RetrievalService(
            self._session,
            provider=self._provider,
            sparse_provider=(
                self._sparse_provider_factory()
                if request.strategy in ("sparse", "dense_sparse")
                else None
            ),
            reranker=(
                self._rerank_provider_factory() if request.rerank is not None else None
            ),
            graph_retriever=self._graph_retriever,
        )
        return service.search(request)


def get_chat_retrieval_searcher(
    session: Annotated[Session, Depends(get_session)],
    provider: Annotated[
        DenseEmbeddingProvider,
        Depends(get_dense_embedding_provider),
    ],
    sparse_provider_factory: Annotated[
        SparseEmbeddingProviderFactory,
        Depends(get_sparse_embedding_provider_factory),
    ],
    rerank_provider_factory: Annotated[
        RerankProviderFactory,
        Depends(get_rerank_provider_factory),
    ],
    graph_retriever: Annotated[
        GraphRetriever | None,
        Depends(get_graph_retriever),
    ],
) -> LazyChatRetrievalSearcher:
    return LazyChatRetrievalSearcher(
        session=session,
        provider=provider,
        sparse_provider_factory=sparse_provider_factory,
        rerank_provider_factory=rerank_provider_factory,
        graph_retriever=graph_retriever,
    )


def get_chat_audit_writer(
    session: Annotated[Session, Depends(get_session)],
) -> SqlAlchemyChatAuditWriter:
    return SqlAlchemyChatAuditWriter(
        session=session,
        chat_audit_repository=ChatAuditRepository(session),
        provider_usage_repository=ProviderUsageRepository(session),
    )


def get_chat_runner(
    workspace_id: UUID | None = None,
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
            workspace_id=workspace_id,
            session=active_session,
            usage_tracker=active_usage_tracker,
        ),
    )


def get_vision_chat_runner(
    workspace_id: UUID | None = None,
    session: Session | DependsMarker = _SESSION_DEPENDENCY,
    usage_tracker: InMemoryProviderUsageTracker | DependsMarker = (
        _VISION_CHAT_RUNNER_USAGE_TRACKER_DEPENDENCY
    ),
) -> ChatRunner | None:
    active_session = None if isinstance(session, DependsMarker) else session
    active_usage_tracker = (
        get_provider_usage_tracker()
        if isinstance(usage_tracker, DependsMarker)
        else usage_tracker
    )
    return cast(
        ChatRunner | None,
        _call_with_supported_kwargs(
            get_runtime_vision_chat_runner,
            workspace_id=workspace_id,
            session=active_session,
            usage_tracker=active_usage_tracker,
        ),
    )


def get_chat_service(
    session: Annotated[Session, Depends(get_session)],
    access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
    retrieval_service: Annotated[
        LazyChatRetrievalSearcher,
        Depends(get_chat_retrieval_searcher),
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
    def _graph_ready(workspace_id: UUID) -> bool:
        # Fail closed: missing table/projection → dense_sparse, never crash chat.
        try:
            from adaptive_rag.db.repositories import GraphprojectionRepository

            projection = GraphprojectionRepository(session).get(
                workspace_id=workspace_id
            )
        except Exception:
            return False
        return projection is not None and projection.status == "ready"

    def _attachment_loader(
        *,
        workspace_id: UUID,
        user_id: UUID | None,
        attachment_ids: Sequence[UUID],
    ) -> tuple[ChatAttachmentContext, ...]:
        from adaptive_rag.chat.attachments import load_chat_attachments

        return load_chat_attachments(
            session,
            workspace_id=workspace_id,
            user_id=user_id,
            attachment_ids=attachment_ids,
        )

    def _vision_runner_factory(workspace_id: UUID) -> ChatRunner | None:
        return get_vision_chat_runner(
            workspace_id=workspace_id,
            session=session,
            usage_tracker=usage_tracker,
        )

    return ChatService(
        runner=runner,
        retrieval_service=retrieval_service,
        audit_writer=audit_writer,
        provider_usage_records=lambda: usage_tracker.records,
        knowledge_proposal_submitter=SqlAlchemyKnowledgeProposalSubmitter(
            session=session,
            workspace_role=access[1],
        ),
        graph_readiness=_graph_ready,
        attachment_loader=_attachment_loader,
        vision_runner_factory=_vision_runner_factory,
    )
