"""Tests de la superficie HTTP de chat/tool calling."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast
from uuid import UUID

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
    ChunkRepository,
    DocumentRepository,
    ProjectRepository,
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
    runner: ToolCallingChatRunner | RecordingNoToolChatRunner,
    usage_tracker: InMemoryProviderUsageTracker | None = None,
) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    def override_provider() -> StaticQueryEmbeddingProvider:
        return provider

    def override_runner() -> ToolCallingChatRunner | RecordingNoToolChatRunner:
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
