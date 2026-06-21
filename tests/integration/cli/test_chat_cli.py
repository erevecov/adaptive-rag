"""Tests del comando CLI de chat/tool calling."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker
from typer.testing import CliRunner

from adaptive_rag.chat import ChatRunnerOutput, ChatRunnerRequest
from adaptive_rag.chat.tools import ChatTools
from adaptive_rag.cli.app import app
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


class ProviderUsageRecordingChatRunner:
    def __init__(
        self,
        *,
        tracker: InMemoryProviderUsageTracker | None,
    ) -> None:
        self.tracker = tracker
        self.requests: list[ChatRunnerRequest] = []

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        self.requests.append(request)
        if self.tracker is not None:
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
                    request_id="cli-chat-request-1",
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


def _make_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        URL.create(
            "sqlite+pysqlite",
            database=str(tmp_path / "chat-cli.sqlite"),
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


def _patch_chat_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session: Session,
    provider: StaticQueryEmbeddingProvider,
    runner: ToolCallingChatRunner | RecordingNoToolChatRunner | ExplodingChatRunner,
) -> None:
    @contextmanager
    def override_session_scope() -> Iterator[Session]:
        yield session

    monkeypatch.setattr(
        "adaptive_rag.cli.chat.session_scope",
        override_session_scope,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.chat.get_cli_dense_embedding_provider",
        lambda: provider,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.chat.get_cli_chat_runner",
        lambda usage_tracker=None: runner,
    )


def test_chat_ask_command_outputs_api_compatible_json(
    monkeypatch: pytest.MonkeyPatch,
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
    _wrong_type_source, _wrong_type_document, _wrong_type_version, _wrong_type = (
        _create_embedded_chunk(
            session,
            project=project,
            source_type="text",
            external_id="wrong-type.txt",
            tags=("docs", "v1"),
            stable_id="wrong-type-doc",
            text="Wrong type evidence",
            snippet="Wrong type evidence",
            embedding=_vector(0.0),
        )
    )
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = ToolCallingChatRunner(retrieval_query="alpha evidence")
    _patch_chat_dependencies(
        monkeypatch,
        session=session,
        provider=provider,
        runner=runner,
    )

    result = CliRunner().invoke(
        app,
        [
            "chat",
            "ask",
            "--project-id",
            str(project.id),
            "--message",
            "What supports alpha?",
            "--retrieval-limit",
            "2",
            "--source-type",
            "markdown",
            "--tag",
            "docs",
            "--tag",
            "v1",
        ],
    )

    assert result.exit_code == 0
    assert provider.inputs == ["alpha evidence"]
    assert len(runner.requests) == 1
    assert runner.requests[0].message == "What supports alpha?"
    assert runner.requests[0].retrieval_limit == 2
    assert runner.requests[0].metadata_filter is not None
    assert runner.requests[0].metadata_filter.source_type == "markdown"
    assert runner.requests[0].metadata_filter.tags == ("docs", "v1")
    data = json.loads(result.stdout)
    assert data["answer"] == "Alpha is backed by retrieved evidence."
    assert [citation["chunk_id"] for citation in data["citations"]] == [
        str(near.id),
        str(far.id),
    ]
    assert data["citations"][0]["citation"] == {
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
    assert chat_session.status == "succeeded"
    assert (
        fresh_session.query(ChatMessage).filter_by(session_id=session_id).count() == 2
    )
    assert fresh_session.query(ToolCall).filter_by(session_id=session_id).count() == 1
    retrieval_run = (
        fresh_session.query(RetrievalRun).filter_by(session_id=session_id).one()
    )
    retrieved_chunks = (
        fresh_session.query(RetrievedChunk)
        .filter_by(retrieval_run_id=retrieval_run.id)
        .order_by(RetrievedChunk.rank)
        .all()
    )
    assert [item.chunk_id for item in retrieved_chunks] == [near.id, far.id]


def test_chat_ask_command_reports_service_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = RecordingNoToolChatRunner()
    _patch_chat_dependencies(
        monkeypatch,
        session=session,
        provider=provider,
        runner=runner,
    )

    result = CliRunner().invoke(
        app,
        [
            "chat",
            "ask",
            "--project-id",
            str(project.id),
            "--message",
            " ",
        ],
    )

    assert result.exit_code == 1
    assert "message must not be empty" in result.output
    assert provider.inputs == []
    assert runner.requests == []


def test_chat_ask_command_persists_live_runner_usage_with_session_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runners: list[ProviderUsageRecordingChatRunner] = []

    @contextmanager
    def override_session_scope() -> Iterator[Session]:
        yield session

    def runner_factory(
        *,
        usage_tracker: InMemoryProviderUsageTracker | None = None,
    ) -> ProviderUsageRecordingChatRunner:
        runner = ProviderUsageRecordingChatRunner(tracker=usage_tracker)
        runners.append(runner)
        return runner

    monkeypatch.setattr(
        "adaptive_rag.cli.chat.session_scope",
        override_session_scope,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.chat.get_cli_dense_embedding_provider",
        lambda: provider,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.chat.get_cli_chat_runner",
        runner_factory,
    )

    result = CliRunner().invoke(
        app,
        [
            "chat",
            "ask",
            "--project-id",
            str(project.id),
            "--message",
            "Record live usage.",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
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
    assert usage.provider_request_id == "cli-chat-request-1"


def test_chat_ask_command_persists_failed_audit_for_unexpected_runner_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = ExplodingChatRunner()
    _patch_chat_dependencies(
        monkeypatch,
        session=session,
        provider=provider,
        runner=runner,
    )

    result = CliRunner().invoke(
        app,
        [
            "chat",
            "ask",
            "--project-id",
            str(project.id),
            "--message",
            "Please answer.",
        ],
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert str(result.exception) == "runner exploded"
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
