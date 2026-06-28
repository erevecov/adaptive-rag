"""Tests de la superficie HTTP de chat/tool calling."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import (
    get_chat_runner,
    get_dense_embedding_provider,
    get_provider_usage_tracker,
    get_rerank_provider_factory,
    get_session,
    get_sparse_embedding_provider_factory,
)
from adaptive_rag.auth import hash_access_token
from adaptive_rag.chat import ChatRunnerOutput, ChatRunnerRequest
from adaptive_rag.chat.tools import ChatTools
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    EMBEDDING_DIMENSIONS,
    ChatMessage,
    ChatSession,
    Chunk,
    ChunkSparseEmbedding,
    Document,
    DocumentVersion,
    GlobalChatRetrievalSettings,
    KnowledgeProposal,
    Project,
    ProjectChatRetrievalSettings,
    ProjectMembership,
    ProviderUsage,
    RetrievalRun,
    RetrievedChunk,
    Source,
    ToolCall,
    User,
    UserAccessToken,
)
from adaptive_rag.db.repositories import (
    ChatAuditRepository,
    ChunkRepository,
    DocumentRepository,
    ProjectMembershipRepository,
    ProjectRepository,
    ProviderUsageRepository,
    SourceRepository,
    SparseEmbeddingRepository,
    UserRepository,
)
from adaptive_rag.db.session import create_session_factory
from adaptive_rag.embeddings import SparseEmbeddingVector
from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderCallRecord,
    ProviderOperation,
    ProviderTokenUsage,
)
from adaptive_rag.rerank import RerankRequest, RerankResult, RerankScore


class StaticQueryEmbeddingProvider:
    provider_name = "fake"
    model_name = "static-query-v1"
    dimensions = EMBEDDING_DIMENSIONS

    def __init__(self, embedding: list[float]) -> None:
        self.embedding = embedding
        self.inputs: list[str] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.inputs.extend(texts)
        return [list(self.embedding) for _text in texts]


class StaticSparseEmbeddingProvider:
    provider_name = "fake"
    model_name = "static-sparse-query-v1"
    dimensions = EMBEDDING_DIMENSIONS

    def __init__(self) -> None:
        self.query_inputs: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[SparseEmbeddingVector]:
        return [_sparse_vector(1.0) for _text in texts]

    def embed_query(self, text: str) -> SparseEmbeddingVector:
        self.query_inputs.append(text)
        return _sparse_vector(1.0)


class PreservingRerankProvider:
    provider_name = "fake-rerank"
    model_name = "preserving-rerank-v1"

    def __init__(self) -> None:
        self.requests: list[RerankRequest] = []

    def rerank(self, request: RerankRequest) -> RerankResult:
        self.requests.append(request)
        return RerankResult(
            provider_name=self.provider_name,
            model_name=self.model_name,
            scores=tuple(
                RerankScore(
                    candidate_id=candidate.candidate_id,
                    score=1.0 / original_rank,
                    original_rank=original_rank,
                    rerank_rank=original_rank,
                )
                for original_rank, candidate in enumerate(
                    request.candidates[: request.top_k],
                    start=1,
                )
            ),
        )


class ReversingRerankProvider(PreservingRerankProvider):
    model_name = "reversing-rerank-v1"

    def rerank(self, request: RerankRequest) -> RerankResult:
        self.requests.append(request)
        selected = tuple(reversed(request.candidates))[: request.top_k]
        original_ranks = {
            candidate.candidate_id: original_rank
            for original_rank, candidate in enumerate(request.candidates, start=1)
        }
        return RerankResult(
            provider_name=self.provider_name,
            model_name=self.model_name,
            scores=tuple(
                RerankScore(
                    candidate_id=candidate.candidate_id,
                    score=1.0 / rerank_rank,
                    original_rank=original_ranks[candidate.candidate_id],
                    rerank_rank=rerank_rank,
                )
                for rerank_rank, candidate in enumerate(selected, start=1)
            ),
        )


class UsageRecordingQueryEmbeddingProvider(StaticQueryEmbeddingProvider):
    def __init__(
        self,
        embedding: list[float],
        *,
        usage_tracker: InMemoryProviderUsageTracker,
    ) -> None:
        super().__init__(embedding)
        self.usage_tracker = usage_tracker

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings = super().embed_texts(texts)
        self.usage_tracker.record(
            ProviderCallRecord(
                provider="fake",
                model="usage-recording-embedding-v1",
                operation="embedding",
                outcome="succeeded",
                duration_ms=7,
                usage=ProviderTokenUsage(input_count=len(texts)),
                usage_source="unavailable",
                request_id="embedding-request-1",
            )
        )
        return embeddings


class FailingQueryEmbeddingProvider(StaticQueryEmbeddingProvider):
    dimensions = EMBEDDING_DIMENSIONS + 1


class UnexpectedFailingQueryEmbeddingProvider(StaticQueryEmbeddingProvider):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.inputs.extend(texts)
        raise RuntimeError("embedding transport unavailable")


class ToolCallingChatRunner:
    def __init__(self, *, retrieval_query: str) -> None:
        self.retrieval_query = retrieval_query
        self.requests: list[ChatRunnerRequest] = []

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        self.requests.append(request)
        result = tools.retrieval.search(
            query=self.retrieval_query,
            limit=request.retrieval_limit,
        )
        return ChatRunnerOutput(
            answer="Alpha is backed by retrieved evidence.",
            cited_chunk_ids=tuple(UUID(item["chunk_id"]) for item in result.results),
        )


class RecordingNoToolChatRunner:
    def __init__(self) -> None:
        self.requests: list[ChatRunnerRequest] = []

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        self.requests.append(request)
        return ChatRunnerOutput(answer="No retrieval was needed.")


class ProviderUsageRecordingChatRunner:
    def __init__(self, *, tracker: InMemoryProviderUsageTracker) -> None:
        self.tracker = tracker
        self.requests: list[ChatRunnerRequest] = []

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        self.requests.append(request)
        self.tracker.record(
            ProviderCallRecord(
                provider="qwen",
                model="qwen-plus",
                operation="chat",
                outcome="succeeded",
                duration_ms=12,
                usage=ProviderTokenUsage(
                    input_tokens=3,
                    output_tokens=4,
                    total_tokens=7,
                ),
                usage_source="provider_reported",
                estimated_cost_usd=0.0001,
                request_id="chat-request-1",
            )
        )
        return ChatRunnerOutput(answer="Live usage was recorded.")


class ExplodingChatRunner:
    def __init__(self) -> None:
        self.requests: list[ChatRunnerRequest] = []

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        self.requests.append(request)
        raise RuntimeError("runner exploded")


class MetadataChatRunner(RecordingNoToolChatRunner):
    provider_name = "qwen"
    model_name = "qwen-plus"
    prompt_version = "m13-chat-v1"


def _make_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        URL.create(
            "sqlite+pysqlite",
            database=str(tmp_path / "chat-api.sqlite"),
        ),
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            User.__table__,
            UserAccessToken.__table__,
            ProjectMembership.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
            ChunkSparseEmbedding.__table__,
            GlobalChatRetrievalSettings.__table__,
            ProjectChatRetrievalSettings.__table__,
            ChatSession.__table__,
            ChatMessage.__table__,
            KnowledgeProposal.__table__,
            ToolCall.__table__,
            RetrievalRun.__table__,
            RetrievedChunk.__table__,
            ProviderUsage.__table__,
        ],
    )
    return create_session_factory(engine)


def _client(
    *,
    session: Session,
    provider: StaticQueryEmbeddingProvider,
    runner: ToolCallingChatRunner | RecordingNoToolChatRunner | ExplodingChatRunner,
    usage_tracker: InMemoryProviderUsageTracker | None = None,
    reranker: PreservingRerankProvider | None = None,
) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    def override_provider() -> StaticQueryEmbeddingProvider:
        return provider

    sparse_provider = StaticSparseEmbeddingProvider()

    def override_sparse_provider_factory() -> Callable[
        [], StaticSparseEmbeddingProvider
    ]:
        return lambda: sparse_provider

    def override_runner() -> (
        ToolCallingChatRunner | RecordingNoToolChatRunner | ExplodingChatRunner
    ):
        return runner

    active_reranker = reranker if reranker is not None else PreservingRerankProvider()

    def override_rerank_provider_factory() -> Callable[[], PreservingRerankProvider]:
        return lambda: active_reranker

    def override_usage_tracker() -> InMemoryProviderUsageTracker:
        assert usage_tracker is not None
        return usage_tracker

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_dense_embedding_provider] = override_provider
    app.dependency_overrides[get_sparse_embedding_provider_factory] = (
        override_sparse_provider_factory
    )
    app.dependency_overrides[get_rerank_provider_factory] = (
        override_rerank_provider_factory
    )
    app.dependency_overrides[get_chat_runner] = override_runner
    if usage_tracker is not None:
        app.dependency_overrides[get_provider_usage_tracker] = override_usage_tracker
    return TestClient(app)


def _vector(first: float, second: float = 0.0) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = first
    values[1] = second
    return values


def _sparse_vector(value: float) -> SparseEmbeddingVector:
    return SparseEmbeddingVector(indices=(0,), values=(value,), tokens=("alpha",))


def _create_project(session: Session, name: str = "demo") -> Project:
    return ProjectRepository(session).create(name=name)


def _create_user(
    session: Session,
    *,
    login: str,
    token: str,
    system_role: str = "user",
) -> User:
    repo = UserRepository(session)
    user = repo.create_user(
        login=login,
        display_name=login,
        system_role=system_role,
    )
    repo.upsert_access_token(
        user_id=user.id,
        token_hash=hash_access_token(token),
        label=f"{login} token",
    )
    return user


def _bearer(raw_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {raw_token}"}


def _create_embedded_chunk(
    session: Session,
    *,
    project: Project,
    source_type: str = "markdown",
    external_id: str,
    tags: tuple[str, ...] = (),
    stable_id: str,
    text: str,
    snippet: str,
    embedding: list[float] | None,
) -> tuple[Source, Document, DocumentVersion, Chunk]:
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type=source_type,
        external_id=external_id,
        tags=tags,
        extra_metadata={"title": external_id},
    )
    document = DocumentRepository(session).create_document(
        project_id=project.id,
        source_id=source.id,
        stable_id=stable_id,
    )
    version = DocumentRepository(session).create_version(
        project_id=project.id,
        document_id=document.id,
        version_number=1,
        normalized_text=text,
        content_hash=f"sha256:{stable_id}",
        index_fingerprint=f"fp:{stable_id}",
    )
    char_start = text.index(snippet)
    chunk = ChunkRepository(session).create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=char_start,
        char_end=char_start + len(snippet),
        token_count=3,
        section_metadata={"heading": stable_id, "section_path": [stable_id]},
        chunker_metadata={"chunker_version": "semantic_markdown_v1"},
        embedding=embedding,
    )
    session.flush()
    if embedding is not None:
        SparseEmbeddingRepository(session).upsert_current(
            project_id=project.id,
            chunk_id=chunk.id,
            vector=_sparse_vector(max(0.01, 1.0 - embedding[0])),
            input_hash=f"sparse:{stable_id}",
            index_fingerprint=f"sparse-fp:{stable_id}",
        )
    return source, document, version, chunk


def _make_provider_call_record() -> ProviderCallRecord:
    return ProviderCallRecord(
        provider="qwen",
        model="qwen-plus",
        operation="chat",
        outcome="succeeded",
        duration_ms=25,
        usage=ProviderTokenUsage(
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            input_count=1,
        ),
        usage_source="provider_reported",
        estimated_cost_usd=0.0001,
        request_id="req-123",
        error_type="RateLimitError",
    )


def _set_session_timestamp(
    chat_session: ChatSession,
    created_at: datetime,
) -> None:
    chat_session.created_at = created_at
    chat_session.updated_at = created_at + timedelta(seconds=1)


def test_chat_endpoint_returns_answer_with_retrieval_citations(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    _far_source, _far_document, _far_version, far = _create_embedded_chunk(
        session,
        project=project,
        external_id="far.md",
        tags=("docs", "v1"),
        stable_id="far-doc",
        text="Far original evidence",
        snippet="Far original evidence",
        embedding=_vector(0.9),
    )
    source, document, version, near = _create_embedded_chunk(
        session,
        project=project,
        external_id="near.md",
        tags=("docs", "v1"),
        stable_id="near-doc",
        text="Header\n\nAlpha original evidence",
        snippet="Alpha original evidence",
        embedding=_vector(0.1),
    )
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = ToolCallingChatRunner(retrieval_query="alpha evidence")
    client = _client(session=session, provider=provider, runner=runner)

    response = client.post(
        f"/projects/{project.id}/chat",
        json={
            "message": "What supports alpha?",
            "retrieval_limit": 2,
            "metadata_filter": {
                "source_type": "markdown",
                "tags": ["docs", "v1"],
            },
        },
    )

    assert response.status_code == 200
    assert provider.inputs == ["alpha evidence"]
    assert len(runner.requests) == 1
    assert runner.requests[0].message == "What supports alpha?"
    assert runner.requests[0].retrieval_limit == 2
    assert runner.requests[0].metadata_filter is not None
    data = response.json()
    assert data["answer"] == "Alpha is backed by retrieved evidence."
    assert [citation["chunk_id"] for citation in data["citations"]] == [
        str(near.id),
        str(far.id),
    ]
    first = data["citations"][0]
    assert first["citation"] == {
        "source_id": str(source.id),
        "source_type": "markdown",
        "source_external_id": "near.md",
        "source_tags": ["docs", "v1"],
        "source_extra_metadata": {"title": "near.md"},
        "document_id": str(document.id),
        "document_stable_id": "near-doc",
        "document_version_id": str(version.id),
        "document_version_number": 1,
        "chunk_id": str(near.id),
        "char_start": 8,
        "char_end": 31,
        "snippet": "Alpha original evidence",
        "section_metadata": {
            "heading": "near-doc",
            "section_path": ["near-doc"],
        },
    }
    assert data["tool_calls"] == [
        {
            "name": "retrieval.search",
            "query": "alpha evidence",
            "limit": 2,
            "result_count": 2,
        }
    ]
    session_id = UUID(data["session_id"])
    fresh_session = session_factory()
    chat_session = fresh_session.get(ChatSession, session_id)
    assert chat_session is not None
    assert chat_session.project_id == project.id
    assert chat_session.status == "succeeded"
    messages = fresh_session.query(ChatMessage).filter_by(session_id=session_id).all()
    assert [message.role for message in messages] == ["user", "assistant"]
    tool_calls = fresh_session.query(ToolCall).filter_by(session_id=session_id).all()
    assert len(tool_calls) == 1
    assert tool_calls[0].tool_name == "retrieval.search"
    retrieval_runs = (
        fresh_session.query(RetrievalRun).filter_by(session_id=session_id).all()
    )
    assert len(retrieval_runs) == 1
    retrieved_chunks = (
        fresh_session.query(RetrievedChunk)
        .filter_by(retrieval_run_id=retrieval_runs[0].id)
        .order_by(RetrievedChunk.rank)
        .all()
    )
    assert [item.chunk_id for item in retrieved_chunks] == [near.id, far.id]


def test_chat_endpoint_uses_project_retrieval_settings_for_rerank_window(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    _source, _document, _version, first = _create_embedded_chunk(
        session,
        project=project,
        external_id="first.md",
        stable_id="first-doc",
        text="Header\n\nAlpha first evidence",
        snippet="Alpha first evidence",
        embedding=_vector(0.1),
    )
    _source, _document, _version, second = _create_embedded_chunk(
        session,
        project=project,
        external_id="second.md",
        stable_id="second-doc",
        text="Header\n\nAlpha second evidence",
        snippet="Alpha second evidence",
        embedding=_vector(0.2),
    )
    from adaptive_rag.db.repositories import ChatRetrievalSettingsRepository

    ChatRetrievalSettingsRepository(session).upsert_project_settings(
        project_id=project.id,
        retrieval_limit=1,
        rerank_enabled=True,
        rerank_candidate_limit=2,
    )
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = ToolCallingChatRunner(retrieval_query="alpha evidence")
    reranker = ReversingRerankProvider()
    client = _client(
        session=session,
        provider=provider,
        runner=runner,
        reranker=reranker,
    )

    response = client.post(
        f"/projects/{project.id}/chat",
        json={"message": "What supports alpha?"},
    )

    assert response.status_code == 200
    assert len(runner.requests) == 1
    assert runner.requests[0].retrieval_limit == 1
    assert len(reranker.requests) == 1
    rerank_request = reranker.requests[0]
    assert rerank_request.top_k == 1
    assert len(rerank_request.candidates) == 2
    data = response.json()
    assert [citation["chunk_id"] for citation in data["citations"]] == [str(second.id)]
    assert data["citations"][0]["rerank_metadata"]["candidate_limit"] == 2
    fresh_session = session_factory()
    retrieval_run = fresh_session.query(RetrievalRun).one()
    assert retrieval_run.top_k == 1
    assert retrieval_run.used_rerank is True
    assert retrieval_run.strategy == "dense_sparse"
    retrieved_chunk = fresh_session.query(RetrievedChunk).one()
    assert retrieved_chunk.chunk_id == second.id
    assert first.id != second.id


def test_chat_endpoint_persists_current_user_as_session_owner(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    user = _create_user(session, login="viewer@example.com", token="viewer-token")
    ProjectMembershipRepository(session).upsert_membership(
        project_id=project.id,
        user_id=user.id,
        role="viewer",
    )
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = RecordingNoToolChatRunner()
    client = _client(session=session, provider=provider, runner=runner)

    response = client.post(
        f"/projects/{project.id}/chat",
        headers=_bearer("viewer-token"),
        json={"message": "No retrieval needed."},
    )

    assert response.status_code == 200
    session_id = UUID(response.json()["session_id"])
    fresh_session = session_factory()
    chat_session = fresh_session.get(ChatSession, session_id)
    assert chat_session is not None
    assert chat_session.user_id == user.id


def test_chat_stream_endpoint_returns_sse_events_and_persists_session(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = RecordingNoToolChatRunner()
    client = _client(session=session, provider=provider, runner=runner)

    response = client.post(
        f"/projects/{project.id}/chat/stream",
        json={"message": "No retrieval needed."},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: session_started\n" in response.text
    assert (
        'event: answer_delta\ndata: {"text":"No retrieval was needed."}\n\n'
        in response.text
    )
    assert "event: final\n" in response.text
    assert len(runner.requests) == 1
    fresh_session = session_factory()
    chat_session = fresh_session.query(ChatSession).one()
    assert chat_session.project_id == project.id
    assert chat_session.status == "succeeded"


def test_chat_stream_endpoint_rejects_invalid_requests_before_stream_start(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = RecordingNoToolChatRunner()
    client = _client(session=session, provider=provider, runner=runner)

    response = client.post(
        f"/projects/{project.id}/chat/stream",
        json={"message": " "},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "message must not be empty"}
    assert runner.requests == []
    fresh_session = session_factory()
    assert fresh_session.query(ChatSession).count() == 0


def test_chat_stream_endpoint_yields_error_event_after_session_failure(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = ExplodingChatRunner()
    client = _client(session=session, provider=provider, runner=runner)

    response = client.post(
        f"/projects/{project.id}/chat/stream",
        json={"message": "Please answer."},
    )

    assert response.status_code == 200
    assert 'event: error\ndata: {"detail":"runner exploded"}\n\n' in response.text
    fresh_session = session_factory()
    chat_session = fresh_session.query(ChatSession).one()
    assert chat_session.status == "failed"
    assert chat_session.error_message == "runner exploded"


def test_chat_endpoint_rejects_unknown_filter_fields(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = RecordingNoToolChatRunner()
    client = _client(session=session, provider=provider, runner=runner)

    response = client.post(
        f"/projects/{project.id}/chat",
        json={
            "message": "What supports alpha?",
            "metadata_filter": {"unsupported": "value"},
        },
    )

    assert response.status_code == 422
    assert provider.inputs == []
    assert runner.requests == []


def test_chat_endpoint_maps_service_errors_to_422(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = RecordingNoToolChatRunner()
    client = _client(session=session, provider=provider, runner=runner)

    response = client.post(
        f"/projects/{project.id}/chat",
        json={"message": " "},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "message must not be empty"}
    assert provider.inputs == []
    assert runner.requests == []


def test_chat_endpoint_provider_usage_failure_does_not_block_success(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = RecordingNoToolChatRunner()
    usage_tracker = InMemoryProviderUsageTracker(
        _records=[
            ProviderCallRecord(
                provider="qwen",
                model="qwen-plus",
                operation=cast(ProviderOperation, cast(Any, "not_supported")),
                outcome="succeeded",
                duration_ms=1,
                usage=ProviderTokenUsage(),
                usage_source="unavailable",
            )
        ]
    )
    client = _client(
        session=session,
        provider=provider,
        runner=runner,
        usage_tracker=usage_tracker,
    )

    response = client.post(
        f"/projects/{project.id}/chat",
        json={"message": "No retrieval needed."},
    )

    assert response.status_code == 200
    data = response.json()
    session_id = UUID(data["session_id"])
    fresh_session = session_factory()
    chat_session = fresh_session.get(ChatSession, session_id)
    assert chat_session is not None
    assert chat_session.status == "succeeded"
    assert (
        fresh_session.query(ProviderUsage).filter_by(session_id=session_id).count() == 0
    )


def test_chat_endpoint_persists_live_runner_usage_with_session_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runners: list[ProviderUsageRecordingChatRunner] = []

    def runtime_chat_runner(
        *,
        usage_tracker: InMemoryProviderUsageTracker,
    ) -> ProviderUsageRecordingChatRunner:
        runner = ProviderUsageRecordingChatRunner(tracker=usage_tracker)
        runners.append(runner)
        return runner

    monkeypatch.setattr(
        "adaptive_rag.api.dependencies.get_runtime_chat_runner",
        runtime_chat_runner,
    )
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    def override_provider() -> StaticQueryEmbeddingProvider:
        return provider

    def override_sparse_provider_factory() -> Callable[
        [], StaticSparseEmbeddingProvider
    ]:
        sparse_provider = StaticSparseEmbeddingProvider()
        return lambda: sparse_provider

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_dense_embedding_provider] = override_provider
    app.dependency_overrides[get_sparse_embedding_provider_factory] = (
        override_sparse_provider_factory
    )
    client = TestClient(app)

    response = client.post(
        f"/projects/{project.id}/chat",
        json={"message": "Record live usage."},
    )

    assert response.status_code == 200
    data = response.json()
    session_id = UUID(data["session_id"])
    assert data["answer"] == "Live usage was recorded."
    assert len(runners) == 1
    assert len(runners[0].requests) == 1
    fresh_session = session_factory()
    usage = fresh_session.query(ProviderUsage).filter_by(session_id=session_id).one()
    assert usage.project_id == project.id
    assert usage.provider == "qwen"
    assert usage.model == "qwen-plus"
    assert usage.operation == "chat"
    assert usage.status == "succeeded"
    assert usage.input_tokens == 3
    assert usage.output_tokens == 4
    assert usage.total_tokens == 7
    assert usage.latency_ms == 12
    assert usage.provider_request_id == "chat-request-1"


def test_chat_endpoint_persists_retrieval_embedding_usage_with_session_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    _source, _document, _version, _chunk = _create_embedded_chunk(
        session,
        project=project,
        external_id="near.md",
        stable_id="near-doc",
        text="Alpha original evidence",
        snippet="Alpha original evidence",
        embedding=_vector(0.1),
    )
    session.commit()
    providers: list[UsageRecordingQueryEmbeddingProvider] = []

    def default_provider_factory(
        *,
        usage_tracker: InMemoryProviderUsageTracker,
    ) -> UsageRecordingQueryEmbeddingProvider:
        provider = UsageRecordingQueryEmbeddingProvider(
            _vector(0.0),
            usage_tracker=usage_tracker,
        )
        providers.append(provider)
        return provider

    monkeypatch.setattr(
        "adaptive_rag.api.dependencies.get_default_dense_embedding_provider",
        default_provider_factory,
    )
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    def override_sparse_provider_factory() -> Callable[
        [], StaticSparseEmbeddingProvider
    ]:
        sparse_provider = StaticSparseEmbeddingProvider()
        return lambda: sparse_provider

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_sparse_embedding_provider_factory] = (
        override_sparse_provider_factory
    )
    app.dependency_overrides[get_rerank_provider_factory] = lambda: (
        lambda: PreservingRerankProvider()
    )
    app.dependency_overrides[get_chat_runner] = lambda: ToolCallingChatRunner(
        retrieval_query="alpha evidence"
    )
    client = TestClient(app)

    response = client.post(
        f"/projects/{project.id}/chat",
        json={"message": "What supports alpha?", "retrieval_limit": 1},
    )

    assert response.status_code == 200
    data = response.json()
    session_id = UUID(data["session_id"])
    assert len(providers) == 1
    assert providers[0].inputs == ["alpha evidence"]
    fresh_session = session_factory()
    usage = fresh_session.query(ProviderUsage).filter_by(session_id=session_id).one()
    assert usage.project_id == project.id
    assert usage.operation == "embedding"
    assert usage.provider == "fake"
    assert usage.model == "usage-recording-embedding-v1"
    assert usage.input_count == 1
    assert usage.provider_request_id == "embedding-request-1"


def test_chat_endpoint_persists_failed_retrieval_tool_call_without_run(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    session.commit()
    provider = FailingQueryEmbeddingProvider(_vector(0.0))
    runner = ToolCallingChatRunner(retrieval_query="alpha evidence")
    client = _client(session=session, provider=provider, runner=runner)

    response = client.post(
        f"/projects/{project.id}/chat",
        json={"message": "What supports alpha?", "retrieval_limit": 3},
    )

    expected_error = (
        "query embedding dimension mismatch: "
        f"expected {EMBEDDING_DIMENSIONS}, got {EMBEDDING_DIMENSIONS + 1}"
    )
    assert response.status_code == 422
    assert response.json() == {"detail": expected_error}
    fresh_session = session_factory()
    chat_session = fresh_session.query(ChatSession).one()
    assert chat_session.status == "failed"
    assert chat_session.error_message == expected_error
    tool_call = (
        fresh_session.query(ToolCall).filter_by(session_id=chat_session.id).one()
    )
    assert tool_call.status == "failed"
    assert tool_call.tool_name == "retrieval.search"
    assert tool_call.arguments_json == {
        "query": "alpha evidence",
        "limit": 3,
        "metadata_filter": None,
        "strategy": "dense_sparse",
    }
    assert tool_call.error_message == expected_error
    assert isinstance(tool_call.latency_ms, int)
    assert tool_call.latency_ms >= 0
    assert (
        fresh_session.query(RetrievalRun).filter_by(session_id=chat_session.id).count()
        == 0
    )


def test_chat_endpoint_fails_retrieval_tool_for_unexpected_provider_error(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    session.commit()
    provider = UnexpectedFailingQueryEmbeddingProvider(_vector(0.0))
    runner = ToolCallingChatRunner(retrieval_query="alpha evidence")
    client = _client(session=session, provider=provider, runner=runner)

    with pytest.raises(RuntimeError, match="embedding transport unavailable"):
        client.post(
            f"/projects/{project.id}/chat",
            json={"message": "What supports alpha?", "retrieval_limit": 4},
        )

    fresh_session = session_factory()
    chat_session = fresh_session.query(ChatSession).one()
    assert chat_session.status == "failed"
    assert chat_session.error_message == "embedding transport unavailable"
    tool_call = (
        fresh_session.query(ToolCall).filter_by(session_id=chat_session.id).one()
    )
    assert tool_call.status == "failed"
    assert tool_call.tool_name == "retrieval.search"
    assert tool_call.arguments_json == {
        "query": "alpha evidence",
        "limit": 4,
        "metadata_filter": None,
        "strategy": "dense_sparse",
    }
    assert tool_call.error_message == "embedding transport unavailable"
    assert isinstance(tool_call.latency_ms, int)
    assert tool_call.latency_ms >= 0
    assert (
        fresh_session.query(RetrievalRun).filter_by(session_id=chat_session.id).count()
        == 0
    )


def test_chat_endpoint_persists_runner_model_metadata(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = MetadataChatRunner()
    client = _client(session=session, provider=provider, runner=runner)

    response = client.post(
        f"/projects/{project.id}/chat",
        json={"message": "No retrieval needed."},
    )

    assert response.status_code == 200
    session_id = UUID(response.json()["session_id"])
    fresh_session = session_factory()
    chat_session = fresh_session.get(ChatSession, session_id)
    assert chat_session is not None
    assert chat_session.model_config_json == {"provider": "qwen", "model": "qwen-plus"}
    assert chat_session.prompt_version == "m13-chat-v1"


def test_chat_endpoint_persists_failed_audit_for_unexpected_runner_error(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = ExplodingChatRunner()
    client = _client(session=session, provider=provider, runner=runner)

    with pytest.raises(RuntimeError, match="runner exploded"):
        client.post(
            f"/projects/{project.id}/chat",
            json={"message": "Please answer."},
        )

    assert len(runner.requests) == 1
    fresh_session = session_factory()
    chat_session = fresh_session.query(ChatSession).one()
    assert chat_session.project_id == project.id
    assert chat_session.status == "failed"
    assert chat_session.error_message == "runner exploded"
    messages = fresh_session.query(ChatMessage).filter_by(session_id=chat_session.id)
    assert [(message.role, message.content) for message in messages] == [
        ("user", "Please answer.")
    ]


def test_chat_sessions_endpoint_lists_project_sessions_with_counts_filters_and_cursor(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session, "demo")
    other_project = _create_project(session, "other")
    _source, _document, _version, chunk = _create_embedded_chunk(
        session,
        project=project,
        external_id="history.md",
        stable_id="history-doc",
        text="Middle original evidence",
        snippet="Middle original evidence",
        embedding=_vector(0.1),
    )
    _other_source, _other_document, _other_version, other_chunk = (
        _create_embedded_chunk(
            session,
            project=other_project,
            external_id="other.md",
            stable_id="other-doc",
            text="Other original evidence",
            snippet="Other original evidence",
            embedding=_vector(0.2),
        )
    )
    repo = ChatAuditRepository(session)
    usage_repo = ProviderUsageRepository(session)
    base_time = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)

    older = repo.create_session(
        project_id=project.id,
        model_config_json={"provider": "fake", "model": "older"},
        prompt_version="history-v1",
    )
    _set_session_timestamp(older, base_time)
    repo.add_message(
        project_id=project.id,
        session_id=older.id,
        role="user",
        content="older question",
    )
    repo.succeed_session(project_id=project.id, session_id=older.id)

    middle = repo.create_session(
        project_id=project.id,
        model_config_json={"provider": "fake", "model": "middle"},
        prompt_version="history-v1",
    )
    middle.title = "Middle custom title"
    middle.title_is_custom = True
    _set_session_timestamp(middle, base_time + timedelta(minutes=1))
    middle_tool = repo.start_tool_call(
        project_id=project.id,
        session_id=middle.id,
        tool_name="retrieval.search",
        arguments_json={"query": "middle"},
    )
    middle_run = repo.create_retrieval_run(
        project_id=project.id,
        session_id=middle.id,
        tool_call_id=middle_tool.id,
        query="middle",
        strategy="dense",
        top_k=1,
        used_rerank=False,
    )
    repo.add_retrieved_chunk(
        project_id=project.id,
        retrieval_run_id=middle_run.id,
        chunk_id=chunk.id,
        rank=1,
        citation_json={"snippet": "middle evidence"},
    )
    usage_repo.create_from_record(
        project_id=project.id,
        session_id=middle.id,
        job_id=None,
        eval_run_id=None,
        record=_make_provider_call_record(),
    )
    repo.fail_session(
        project_id=project.id,
        session_id=middle.id,
        error_message="runner failed",
    )
    session.add(
        KnowledgeProposal(
            project_id=project.id,
            origin_session_id=middle.id,
            proposed_text="Pending chat learning",
            status="pending",
        )
    )

    newest = repo.create_session(
        project_id=project.id,
        model_config_json={"provider": "fake", "model": "newest"},
    )
    _set_session_timestamp(newest, base_time + timedelta(minutes=2))
    repo.succeed_session(project_id=project.id, session_id=newest.id)
    session.add(
        KnowledgeProposal(
            project_id=project.id,
            origin_session_id=newest.id,
            proposed_text="Approved chat learning",
            status="approved",
        )
    )

    archived = repo.create_session(project_id=project.id)
    _set_session_timestamp(archived, base_time + timedelta(minutes=3))
    repo.add_message(
        project_id=project.id,
        session_id=archived.id,
        role="user",
        content="archived question",
    )
    repo.archive_session(project_id=project.id, session_id=archived.id)

    other_session = repo.create_session(project_id=other_project.id)
    _set_session_timestamp(other_session, base_time + timedelta(minutes=4))
    other_run = repo.create_retrieval_run(
        project_id=other_project.id,
        session_id=other_session.id,
        tool_call_id=None,
        query="other",
        strategy="dense",
        top_k=1,
        used_rerank=False,
    )
    repo.add_retrieved_chunk(
        project_id=other_project.id,
        retrieval_run_id=other_run.id,
        chunk_id=other_chunk.id,
        rank=1,
        citation_json={"snippet": "other evidence"},
    )
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = RecordingNoToolChatRunner()
    client = _client(session=session, provider=provider, runner=runner)

    response = client.get(
        f"/projects/{project.id}/chat/sessions",
        params={"limit": 2},
    )

    assert response.status_code == 200
    data = response.json()
    assert [item["session_id"] for item in data["items"]] == [
        str(newest.id),
        str(middle.id),
    ]
    assert data["next_cursor"] is not None
    middle_item = data["items"][1]
    assert middle_item["status"] == "failed"
    assert middle_item["title"] == "Middle custom title"
    assert middle_item["title_is_custom"] is True
    assert middle_item["archived_at"] is None
    assert middle_item["has_pending_training"] is True
    assert middle_item["has_approved_training"] is False
    assert middle_item["model_config"] == {
        "provider": "fake",
        "model": "middle",
    }
    assert data["items"][0]["has_pending_training"] is False
    assert data["items"][0]["has_approved_training"] is True
    assert middle_item["prompt_version"] == "history-v1"
    assert middle_item["message_count"] == 0
    assert middle_item["tool_call_count"] == 1
    assert middle_item["retrieval_run_count"] == 1
    assert middle_item["provider_usage_count"] == 1
    assert middle_item["total_estimated_cost_usd"] == pytest.approx(0.0001)
    assert middle_item["error_message"] == "runner failed"

    second_page = client.get(
        f"/projects/{project.id}/chat/sessions",
        params={"limit": 2, "cursor": data["next_cursor"]},
    )
    assert second_page.status_code == 200
    assert [item["session_id"] for item in second_page.json()["items"]] == [
        str(older.id)
    ]
    assert second_page.json()["items"][0]["title"] == "older question"
    assert second_page.json()["next_cursor"] is None

    archived_page = client.get(
        f"/projects/{project.id}/chat/sessions",
        params={"archived": True, "limit": 10},
    )
    assert archived_page.status_code == 200
    assert [item["session_id"] for item in archived_page.json()["items"]] == [
        str(archived.id)
    ]
    assert archived_page.json()["items"][0]["archived_at"] is not None

    failed_page = client.get(
        f"/projects/{project.id}/chat/sessions",
        params={"status": "failed", "limit": 10},
    )
    assert failed_page.status_code == 200
    assert [item["session_id"] for item in failed_page.json()["items"]] == [
        str(middle.id)
    ]

    invalid_limit = client.get(
        f"/projects/{project.id}/chat/sessions",
        params={"limit": 0},
    )
    assert invalid_limit.status_code == 422
    assert invalid_limit.json() == {"detail": "limit must be between 1 and 100"}

    invalid_status = client.get(
        f"/projects/{project.id}/chat/sessions",
        params={"status": "archived"},
    )
    assert invalid_status.status_code == 422
    assert invalid_status.json() == {"detail": "invalid chat session status"}


def test_chat_session_sidebar_actions_rename_archive_and_unarchive(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session, "demo")
    repo = ChatAuditRepository(session)
    chat_session = repo.create_session(project_id=project.id)
    repo.add_message(
        project_id=project.id,
        session_id=chat_session.id,
        role="user",
        content="original title",
    )
    repo.succeed_session(project_id=project.id, session_id=chat_session.id)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = RecordingNoToolChatRunner()
    client = _client(session=session, provider=provider, runner=runner)

    rename = client.patch(
        f"/projects/{project.id}/chat/sessions/{chat_session.id}/title",
        json={"title": "  Renamed session  "},
    )

    assert rename.status_code == 200
    assert rename.json() == {
        "session_id": str(chat_session.id),
        "title": "Renamed session",
        "title_is_custom": True,
    }

    blank_rename = client.patch(
        f"/projects/{project.id}/chat/sessions/{chat_session.id}/title",
        json={"title": "   "},
    )
    assert blank_rename.status_code == 422
    assert blank_rename.json() == {"detail": "session title must not be empty"}

    archive = client.post(
        f"/projects/{project.id}/chat/sessions/{chat_session.id}/archive"
    )
    active_list = client.get(f"/projects/{project.id}/chat/sessions")
    archived_list = client.get(
        f"/projects/{project.id}/chat/sessions",
        params={"archived": True},
    )

    assert archive.status_code == 204
    assert active_list.json()["items"] == []
    assert [item["session_id"] for item in archived_list.json()["items"]] == [
        str(chat_session.id)
    ]
    assert archived_list.json()["items"][0]["title"] == "Renamed session"
    assert archived_list.json()["items"][0]["archived_at"] is not None

    unarchive = client.post(
        f"/projects/{project.id}/chat/sessions/{chat_session.id}/unarchive"
    )
    active_again = client.get(f"/projects/{project.id}/chat/sessions")

    assert unarchive.status_code == 204
    assert [item["session_id"] for item in active_again.json()["items"]] == [
        str(chat_session.id)
    ]


def test_chat_sessions_endpoint_scopes_history_to_current_user(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session, "demo")
    first_user = _create_user(session, login="first@example.com", token="first-token")
    second_user = _create_user(
        session,
        login="second@example.com",
        token="second-token",
    )
    superadmin = _create_user(
        session,
        login="root@example.com",
        token="root-token",
        system_role="superadmin",
    )
    membership_repo = ProjectMembershipRepository(session)
    membership_repo.upsert_membership(
        project_id=project.id,
        user_id=first_user.id,
        role="viewer",
    )
    membership_repo.upsert_membership(
        project_id=project.id,
        user_id=second_user.id,
        role="viewer",
    )
    repo = ChatAuditRepository(session)
    first_session = repo.create_session(project_id=project.id, user_id=first_user.id)
    repo.add_message(
        project_id=project.id,
        session_id=first_session.id,
        role="user",
        content="first question",
    )
    repo.succeed_session(project_id=project.id, session_id=first_session.id)
    second_session = repo.create_session(project_id=project.id, user_id=second_user.id)
    repo.add_message(
        project_id=project.id,
        session_id=second_session.id,
        role="user",
        content="second question",
    )
    repo.succeed_session(project_id=project.id, session_id=second_session.id)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = RecordingNoToolChatRunner()
    client = _client(session=session, provider=provider, runner=runner)

    first_history = client.get(
        f"/projects/{project.id}/chat/sessions",
        headers=_bearer("first-token"),
    )
    forbidden_detail = client.get(
        f"/projects/{project.id}/chat/sessions/{second_session.id}",
        headers=_bearer("first-token"),
    )
    superadmin_history = client.get(
        f"/projects/{project.id}/chat/sessions",
        headers=_bearer("root-token"),
    )

    assert superadmin.system_role == "superadmin"
    assert first_history.status_code == 200
    assert [item["session_id"] for item in first_history.json()["items"]] == [
        str(first_session.id)
    ]
    assert forbidden_detail.status_code == 404
    assert forbidden_detail.json() == {"detail": "chat session not found"}
    assert superadmin_history.status_code == 200
    assert {item["session_id"] for item in superadmin_history.json()["items"]} == {
        str(first_session.id),
        str(second_session.id),
    }


def test_chat_session_detail_endpoint_returns_audit_records_and_scopes_project(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session, "demo")
    other_project = _create_project(session, "other")
    _source, _document, _version, first_chunk = _create_embedded_chunk(
        session,
        project=project,
        external_id="first.md",
        stable_id="first-doc",
        text="Alpha first evidence",
        snippet="Alpha first evidence",
        embedding=_vector(0.1),
    )
    _second_source, _second_document, _second_version, second_chunk = (
        _create_embedded_chunk(
            session,
            project=project,
            external_id="second.md",
            stable_id="second-doc",
            text="Alpha second evidence",
            snippet="Alpha second evidence",
            embedding=_vector(0.2),
        )
    )
    repo = ChatAuditRepository(session)
    usage_repo = ProviderUsageRepository(session)
    chat_session = repo.create_session(
        project_id=project.id,
        model_config_json={"provider": "fake"},
        prompt_version="history-v1",
    )
    repo.add_message(
        project_id=project.id,
        session_id=chat_session.id,
        role="user",
        content="What supports alpha?",
        metadata_json={"retrieval_limit": 2},
    )
    tool_call = repo.start_tool_call(
        project_id=project.id,
        session_id=chat_session.id,
        tool_name="retrieval.search",
        arguments_json={"query": "alpha"},
    )
    repo.complete_tool_call(
        project_id=project.id,
        tool_call_id=tool_call.id,
        result_summary_json={"result_count": 2},
        latency_ms=5,
    )
    retrieval_run = repo.create_retrieval_run(
        project_id=project.id,
        session_id=chat_session.id,
        tool_call_id=tool_call.id,
        query="alpha",
        strategy="dense",
        top_k=2,
        used_rerank=True,
        filters_json={"source_type": "markdown"},
        latency_ms=5,
    )
    repo.add_retrieved_chunk(
        project_id=project.id,
        retrieval_run_id=retrieval_run.id,
        chunk_id=second_chunk.id,
        rank=2,
        citation_json={"snippet": "second"},
        dense_score=0.2,
    )
    repo.add_retrieved_chunk(
        project_id=project.id,
        retrieval_run_id=retrieval_run.id,
        chunk_id=first_chunk.id,
        rank=1,
        citation_json={"snippet": "first"},
        dense_score=0.1,
    )
    repo.add_message(
        project_id=project.id,
        session_id=chat_session.id,
        role="assistant",
        content="Alpha is supported.",
    )
    usage_repo.create_from_record(
        project_id=project.id,
        session_id=chat_session.id,
        job_id=None,
        eval_run_id=None,
        record=_make_provider_call_record(),
    )
    repo.succeed_session(project_id=project.id, session_id=chat_session.id)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = RecordingNoToolChatRunner()
    client = _client(session=session, provider=provider, runner=runner)

    response = client.get(
        f"/projects/{project.id}/chat/sessions/{chat_session.id}",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session"]["session_id"] == str(chat_session.id)
    assert data["session"]["status"] == "succeeded"
    assert data["session"]["model_config"] == {"provider": "fake"}
    assert data["session"]["prompt_version"] == "history-v1"
    assert [(item["role"], item["content"]) for item in data["messages"]] == [
        ("user", "What supports alpha?"),
        ("assistant", "Alpha is supported."),
    ]
    assert data["messages"][0]["metadata"] == {"retrieval_limit": 2}
    assert data["tool_calls"][0]["tool_call_id"] == str(tool_call.id)
    assert data["tool_calls"][0]["tool_name"] == "retrieval.search"
    assert data["tool_calls"][0]["arguments"] == {"query": "alpha"}
    assert data["tool_calls"][0]["result_summary"] == {"result_count": 2}
    assert data["tool_calls"][0]["latency_ms"] == 5
    retrieval_run_data = data["retrieval_runs"][0]
    assert retrieval_run_data["retrieval_run_id"] == str(retrieval_run.id)
    assert retrieval_run_data["tool_call_id"] == str(tool_call.id)
    assert retrieval_run_data["query"] == "alpha"
    assert retrieval_run_data["strategy"] == "dense"
    assert retrieval_run_data["top_k"] == 2
    assert retrieval_run_data["used_rerank"] is True
    assert retrieval_run_data["filters"] == {"source_type": "markdown"}
    assert [item["citation"] for item in retrieval_run_data["retrieved_chunks"]] == [
        {"snippet": "first"},
        {"snippet": "second"},
    ]
    assert [item["chunk_id"] for item in retrieval_run_data["retrieved_chunks"]] == [
        str(first_chunk.id),
        str(second_chunk.id),
    ]
    assert data["provider_usage"][0]["provider"] == "qwen"
    assert data["provider_usage"][0]["model"] == "qwen-plus"
    assert data["provider_usage"][0]["operation"] == "chat"
    assert data["provider_usage"][0]["estimated_cost_usd"] == pytest.approx(0.0001)

    cross_project = client.get(
        f"/projects/{other_project.id}/chat/sessions/{chat_session.id}",
    )
    assert cross_project.status_code == 404
    assert cross_project.json() == {"detail": "chat session not found"}
