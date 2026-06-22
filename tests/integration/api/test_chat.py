"""Tests de la superficie HTTP de chat/tool calling."""

from __future__ import annotations

from collections.abc import Iterator
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
    get_session,
)
from adaptive_rag.chat import ChatRunnerOutput, ChatRunnerRequest
from adaptive_rag.chat.tools import ChatTools
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    EMBEDDING_DIMENSIONS,
    ChatMessage,
    ChatSession,
    Chunk,
    Document,
    DocumentVersion,
    Project,
    ProviderUsage,
    RetrievalRun,
    RetrievedChunk,
    Source,
    ToolCall,
)
from adaptive_rag.db.repositories import (
    ChatAuditRepository,
    ChunkRepository,
    DocumentRepository,
    ProjectRepository,
    ProviderUsageRepository,
    SourceRepository,
)
from adaptive_rag.db.session import create_session_factory
from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderCallRecord,
    ProviderOperation,
    ProviderTokenUsage,
)


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
            cited_chunk_ids=tuple(
                UUID(item["chunk_id"]) for item in result.results
            ),
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
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
            ChatSession.__table__,
            ChatMessage.__table__,
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
) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    def override_provider() -> StaticQueryEmbeddingProvider:
        return provider

    def override_runner() -> (
        ToolCallingChatRunner | RecordingNoToolChatRunner | ExplodingChatRunner
    ):
        return runner

    def override_usage_tracker() -> InMemoryProviderUsageTracker:
        assert usage_tracker is not None
        return usage_tracker

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_dense_embedding_provider] = override_provider
    app.dependency_overrides[get_chat_runner] = override_runner
    if usage_tracker is not None:
        app.dependency_overrides[get_provider_usage_tracker] = override_usage_tracker
    return TestClient(app)


def _vector(first: float, second: float = 0.0) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = first
    values[1] = second
    return values


def _create_project(session: Session, name: str = "demo") -> Project:
    return ProjectRepository(session).create(name=name)


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
    assert (
        'event: error\ndata: {"detail":"runner exploded"}\n\n'
        in response.text
    )
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
        fresh_session.query(ProviderUsage).filter_by(session_id=session_id).count()
        == 0
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

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_dense_embedding_provider] = override_provider
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

    app.dependency_overrides[get_session] = override_session
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
    tool_call = fresh_session.query(ToolCall).filter_by(
        session_id=chat_session.id
    ).one()
    assert tool_call.status == "failed"
    assert tool_call.tool_name == "retrieval.search"
    assert tool_call.arguments_json == {
        "query": "alpha evidence",
        "limit": 3,
        "metadata_filter": None,
        "strategy": "dense",
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
    tool_call = fresh_session.query(ToolCall).filter_by(
        session_id=chat_session.id
    ).one()
    assert tool_call.status == "failed"
    assert tool_call.tool_name == "retrieval.search"
    assert tool_call.arguments_json == {
        "query": "alpha evidence",
        "limit": 4,
        "metadata_filter": None,
        "strategy": "dense",
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
    messages = fresh_session.query(ChatMessage).filter_by(
        session_id=chat_session.id
    )
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

    newest = repo.create_session(
        project_id=project.id,
        model_config_json={"provider": "fake", "model": "newest"},
    )
    _set_session_timestamp(newest, base_time + timedelta(minutes=2))
    repo.succeed_session(project_id=project.id, session_id=newest.id)

    other_session = repo.create_session(project_id=other_project.id)
    _set_session_timestamp(other_session, base_time + timedelta(minutes=3))
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
    assert middle_item["model_config"] == {
        "provider": "fake",
        "model": "middle",
    }
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
    assert second_page.json()["next_cursor"] is None

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
