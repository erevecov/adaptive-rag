"""Tests del comando CLI de chat/tool calling."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
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
    ChunkSparseEmbedding,
    Document,
    DocumentVersion,
    GlobalChatRetrievalSettings,
    KnowledgeProposal,
    Project,
    ProjectChatRetrievalSettings,
    ProviderUsage,
    RetrievalRun,
    RetrievedChunk,
    Source,
    ToolCall,
)
from adaptive_rag.db.repositories import (
    ChatAuditRepository,
    ChatRetrievalSettingsRepository,
    ChunkRepository,
    DocumentRepository,
    ProjectRepository,
    ProviderUsageRepository,
    SourceRepository,
    SparseEmbeddingRepository,
)
from adaptive_rag.db.session import create_session_factory
from adaptive_rag.embeddings import SparseEmbeddingVector
from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderCallRecord,
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
                request_id="cli-embedding-request-1",
            )
        )
        return embeddings


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


def _vector(first: float, second: float = 0.0) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = first
    values[1] = second
    return values


def _sparse_vector(value: float) -> SparseEmbeddingVector:
    return SparseEmbeddingVector(indices=(0,), values=(value,), tokens=("alpha",))


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
        request_id="cli-history-request-1",
        error_type="RateLimitError",
    )


def _set_session_timestamp(
    chat_session: ChatSession,
    created_at: datetime,
) -> None:
    chat_session.created_at = created_at
    chat_session.updated_at = created_at + timedelta(seconds=1)


def _add_provider_usage(
    session: Session,
    *,
    project_id: UUID,
    created_at: datetime,
    session_id: UUID | None = None,
    operation: str = "chat",
    provider: str = "qwen",
    model: str = "qwen-plus",
    status: str = "succeeded",
    usage_source: str = "provider_reported",
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    input_count: int | None = None,
    estimated_cost_usd: float | None = None,
    latency_ms: int | None = None,
    error_message: str | None = None,
) -> ProviderUsage:
    usage = ProviderUsage(
        project_id=project_id,
        session_id=session_id,
        operation=operation,
        provider=provider,
        model=model,
        status=status,
        usage_source=usage_source,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        input_count=input_count,
        estimated_cost_usd=estimated_cost_usd,
        currency="USD" if estimated_cost_usd is not None else None,
        latency_ms=latency_ms,
        error_message=error_message,
        created_at=created_at,
    )
    session.add(usage)
    session.flush()
    return usage


def _patch_chat_history_session_scope(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session: Session,
) -> None:
    @contextmanager
    def override_session_scope() -> Iterator[Session]:
        yield session

    monkeypatch.setattr(
        "adaptive_rag.cli.chat.session_scope",
        override_session_scope,
    )


def _patch_chat_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session: Session,
    provider: StaticQueryEmbeddingProvider,
    runner: ToolCallingChatRunner | RecordingNoToolChatRunner | ExplodingChatRunner,
    reranker: PreservingRerankProvider | None = None,
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
        "adaptive_rag.cli.chat.get_cli_sparse_embedding_provider",
        lambda: StaticSparseEmbeddingProvider(),
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.chat.get_cli_rerank_provider",
        lambda: reranker if reranker is not None else PreservingRerankProvider(),
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


def test_chat_ask_command_uses_project_retrieval_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session)
    _source, _document, _version, _first = _create_embedded_chunk(
        session,
        project=project,
        external_id="first.md",
        stable_id="first-doc",
        text="Alpha first evidence",
        snippet="Alpha first evidence",
        embedding=_vector(0.1),
    )
    _source, _document, _version, _second = _create_embedded_chunk(
        session,
        project=project,
        external_id="second.md",
        stable_id="second-doc",
        text="Alpha second evidence",
        snippet="Alpha second evidence",
        embedding=_vector(0.2),
    )
    ChatRetrievalSettingsRepository(session).upsert_project_settings(
        project_id=project.id,
        retrieval_limit=1,
        rerank_enabled=True,
        rerank_candidate_limit=2,
    )
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    runner = ToolCallingChatRunner(retrieval_query="alpha evidence")
    reranker = PreservingRerankProvider()
    _patch_chat_dependencies(
        monkeypatch,
        session=session,
        provider=provider,
        runner=runner,
        reranker=reranker,
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
        ],
    )

    assert result.exit_code == 0
    assert len(runner.requests) == 1
    assert runner.requests[0].retrieval_limit == 1
    assert len(reranker.requests) == 1
    assert reranker.requests[0].top_k == 1
    assert len(reranker.requests[0].candidates) == 2
    data = json.loads(result.stdout)
    assert len(data["citations"]) == 1
    assert data["citations"][0]["rerank_metadata"]["candidate_limit"] == 2


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
        "adaptive_rag.cli.chat.get_cli_sparse_embedding_provider",
        lambda: StaticSparseEmbeddingProvider(),
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.chat.get_cli_rerank_provider",
        lambda: PreservingRerankProvider(),
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


def test_chat_ask_command_persists_retrieval_embedding_usage_with_session_id(
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
    runners: list[ToolCallingChatRunner] = []

    @contextmanager
    def override_session_scope() -> Iterator[Session]:
        yield session

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

    def runner_factory(
        *,
        usage_tracker: InMemoryProviderUsageTracker | None = None,
    ) -> ToolCallingChatRunner:
        runner = ToolCallingChatRunner(retrieval_query="alpha evidence")
        runners.append(runner)
        return runner

    monkeypatch.setattr(
        "adaptive_rag.cli.chat.session_scope",
        override_session_scope,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.dependencies.get_default_dense_embedding_provider",
        default_provider_factory,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.chat.get_cli_sparse_embedding_provider",
        lambda: StaticSparseEmbeddingProvider(),
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.chat.get_cli_rerank_provider",
        lambda: PreservingRerankProvider(),
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
            "What supports alpha?",
            "--retrieval-limit",
            "1",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    session_id = UUID(data["session_id"])
    assert len(providers) == 1
    assert providers[0].inputs == ["alpha evidence"]
    assert len(runners) == 1
    fresh_session = session_factory()
    usage = fresh_session.query(ProviderUsage).filter_by(session_id=session_id).one()
    assert usage.project_id == project.id
    assert usage.operation == "embedding"
    assert usage.provider == "fake"
    assert usage.model == "usage-recording-embedding-v1"
    assert usage.input_count == 1
    assert usage.provider_request_id == "cli-embedding-request-1"


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
    messages = fresh_session.query(ChatMessage).filter_by(session_id=chat_session.id)
    assert [(message.role, message.content) for message in messages] == [
        ("user", "Please answer.")
    ]


def test_chat_sessions_list_command_outputs_api_compatible_json(
    monkeypatch: pytest.MonkeyPatch,
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
    _patch_chat_history_session_scope(monkeypatch, session=session)

    result = CliRunner().invoke(
        app,
        [
            "chat",
            "sessions",
            "list",
            "--project-id",
            str(project.id),
            "--limit",
            "2",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
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

    second_page = CliRunner().invoke(
        app,
        [
            "chat",
            "sessions",
            "list",
            "--project-id",
            str(project.id),
            "--limit",
            "2",
            "--cursor",
            data["next_cursor"],
        ],
    )
    assert second_page.exit_code == 0
    assert [item["session_id"] for item in json.loads(second_page.stdout)["items"]] == [
        str(older.id)
    ]
    assert json.loads(second_page.stdout)["next_cursor"] is None

    failed_page = CliRunner().invoke(
        app,
        [
            "chat",
            "sessions",
            "list",
            "--project-id",
            str(project.id),
            "--status",
            "failed",
        ],
    )
    assert failed_page.exit_code == 0
    assert [item["session_id"] for item in json.loads(failed_page.stdout)["items"]] == [
        str(middle.id)
    ]

    invalid_limit = CliRunner().invoke(
        app,
        [
            "chat",
            "sessions",
            "list",
            "--project-id",
            str(project.id),
            "--limit",
            "0",
        ],
    )
    assert invalid_limit.exit_code == 1
    assert "limit must be between 1 and 100" in invalid_limit.output


def test_chat_observability_summary_command_outputs_api_equivalent_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    project = _create_project(session, "demo")
    other_project = _create_project(session, "other")
    base_time = datetime(2026, 1, 1, tzinfo=UTC)

    failed = ChatAuditRepository(session).create_session(project_id=project.id)
    failed.status = "failed"
    failed.error_message = "runner failed"
    _set_session_timestamp(failed, base_time + timedelta(hours=1))
    succeeded = ChatAuditRepository(session).create_session(project_id=project.id)
    succeeded.status = "succeeded"
    _set_session_timestamp(succeeded, base_time + timedelta(hours=2))
    other_failed = ChatAuditRepository(session).create_session(
        project_id=other_project.id
    )
    other_failed.status = "failed"
    other_failed.error_message = "other failure"
    _set_session_timestamp(other_failed, base_time + timedelta(hours=1))

    _add_provider_usage(
        session,
        project_id=project.id,
        session_id=failed.id,
        created_at=base_time + timedelta(hours=1, seconds=1),
        status="failed",
        usage_source="unavailable",
        estimated_cost_usd=None,
        latency_ms=100,
        error_message="runner failed",
    )
    _add_provider_usage(
        session,
        project_id=project.id,
        session_id=failed.id,
        created_at=base_time + timedelta(hours=1, seconds=2),
        input_tokens=10,
        output_tokens=4,
        total_tokens=14,
        input_count=1,
        estimated_cost_usd=0.05,
        latency_ms=300,
    )
    _add_provider_usage(
        session,
        project_id=project.id,
        session_id=succeeded.id,
        created_at=base_time + timedelta(hours=2, seconds=1),
        estimated_cost_usd=0.40,
        latency_ms=400,
    )
    _add_provider_usage(
        session,
        project_id=other_project.id,
        created_at=base_time + timedelta(hours=1),
        estimated_cost_usd=9.99,
        latency_ms=999,
    )
    session.commit()
    _patch_chat_history_session_scope(monkeypatch, session=session)

    result = CliRunner().invoke(
        app,
        [
            "chat",
            "observability",
            "summary",
            "--project-id",
            str(project.id),
            "--created-at-from",
            base_time.isoformat(),
            "--created-at-to",
            (base_time + timedelta(hours=2)).isoformat(),
            "--status",
            "failed",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["project_id"] == str(project.id)
    assert data["filters"] == {
        "created_at_from": "2026-01-01T00:00:00Z",
        "created_at_to": "2026-01-01T02:00:00Z",
        "status": "failed",
    }
    assert data["sessions"] == {
        "total": 1,
        "by_status": {"running": 0, "succeeded": 0, "failed": 1},
    }
    assert data["provider_usage"]["total_records"] == 2
    assert data["provider_usage"]["total_estimated_cost_usd"] == pytest.approx(0.05)
    assert data["provider_usage"]["missing_cost_count"] == 1
    assert data["provider_usage"]["groups"] == [
        {
            "operation": "chat",
            "provider": "qwen",
            "model": "qwen-plus",
            "record_count": 2,
            "estimated_cost_usd": 0.05,
            "input_tokens": 10,
            "output_tokens": 4,
            "total_tokens": 14,
            "input_count": 1,
            "latency_ms": {
                "count": 2,
                "min": 100,
                "avg": 200.0,
                "p50": 100,
                "p95": 300,
                "max": 300,
            },
        }
    ]
    assert data["errors"] == {
        "session_error_count": 1,
        "provider_error_count": 1,
        "top_messages": [{"message": "runner failed", "count": 2}],
    }

    invalid_status = CliRunner().invoke(
        app,
        [
            "chat",
            "observability",
            "summary",
            "--project-id",
            str(project.id),
            "--status",
            "done",
        ],
    )
    assert invalid_status.exit_code == 1
    assert "invalid chat session status" in invalid_status.output


def test_chat_sessions_show_command_outputs_detail_and_scopes_project(
    monkeypatch: pytest.MonkeyPatch,
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
    _patch_chat_history_session_scope(monkeypatch, session=session)

    result = CliRunner().invoke(
        app,
        [
            "chat",
            "sessions",
            "show",
            "--project-id",
            str(project.id),
            "--session-id",
            str(chat_session.id),
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
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

    cross_project = CliRunner().invoke(
        app,
        [
            "chat",
            "sessions",
            "show",
            "--project-id",
            str(other_project.id),
            "--session-id",
            str(chat_session.id),
        ],
    )
    assert cross_project.exit_code == 1
    assert "chat session not found" in cross_project.output
