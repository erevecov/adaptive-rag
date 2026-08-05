"""Multi-turn session continuity, history, and deterministic condenser."""

from __future__ import annotations

from uuid import UUID, uuid4

from adaptive_rag.chat import (
    ChatRequest,
    ChatRunnerOutput,
    ChatRunnerRequest,
    ChatService,
    DeterministicQueryCondenser,
    RetrievalGroundedChatRunner,
)
from adaptive_rag.chat.audit import InMemoryChatAuditWriter
from adaptive_rag.chat.models import ChatHistoryTurn
from adaptive_rag.chat.tools import ChatRetrievalTool, ChatTools
from adaptive_rag.retrieval import (
    DenseRetrievalCitation,
    RetrievalSearchRequest,
    RetrievalSearchResult,
)


class RecordingRunner:
    def __init__(self) -> None:
        self.requests: list[ChatRunnerRequest] = []

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        self.requests.append(request)
        query = request.retrieval_query or request.message
        result = tools.retrieval.search(query=query, limit=request.retrieval_limit)
        chunk_ids = tuple(UUID(item["chunk_id"]) for item in result.results)
        return ChatRunnerOutput(
            answer=f"answered:{query}",
            cited_chunk_ids=chunk_ids,
        )


class StaticRetrieval:
    def __init__(self, results: list[RetrievalSearchResult]) -> None:
        self.results = results
        self.requests: list[RetrievalSearchRequest] = []

    def search(self, request: RetrievalSearchRequest) -> list[RetrievalSearchResult]:
        self.requests.append(request)
        return list(self.results)


def _result(chunk_id: UUID, snippet: str) -> RetrievalSearchResult:
    source_id = uuid4()
    document_id = uuid4()
    document_version_id = uuid4()
    citation = DenseRetrievalCitation(
        source_id=source_id,
        source_type="markdown",
        source_external_id="doc.md",
        source_tags=(),
        source_extra_metadata=None,
        document_id=document_id,
        document_stable_id="doc",
        document_version_id=document_version_id,
        document_version_number=1,
        chunk_id=chunk_id,
        char_start=0,
        char_end=len(snippet),
        snippet=snippet,
        section_metadata=None,
    )
    return RetrievalSearchResult(
        chunk_id=chunk_id,
        distance=0.1,
        score=0.9,
        citation=citation,
        embedding_metadata={"provider": "fake"},
    )


def test_deterministic_condenser_stitches_follow_up() -> None:
    condenser = DeterministicQueryCondenser()
    history = (
        ChatHistoryTurn(role="user", content="What is Adaptive RAG indexing?"),
        ChatHistoryTurn(role="assistant", content="It chunks and embeds."),
    )
    query = condenser.condense(history=history, message="Why does it matter?")
    assert "Adaptive RAG indexing" in query
    assert "Why does it matter?" in query


def test_multi_turn_same_session_and_history() -> None:
    audit = InMemoryChatAuditWriter()
    runner = RecordingRunner()
    chunk_id = uuid4()
    retrieval = StaticRetrieval([_result(chunk_id, "public indexing evidence")])
    service = ChatService(
        runner=runner,
        retrieval_service=retrieval,
        audit_writer=audit,
        query_condenser=DeterministicQueryCondenser(),
    )
    project_id = uuid4()

    first = service.respond(
        ChatRequest(
            project_id=project_id,
            message="What is Adaptive RAG indexing?",
        )
    )
    assert first.session_id is not None

    second = service.respond(
        ChatRequest(
            project_id=project_id,
            session_id=first.session_id,
            message="Why does it matter?",
        )
    )
    assert second.session_id == first.session_id
    assert len(runner.requests) == 2
    follow_up = runner.requests[1]
    assert len(follow_up.history) == 2
    assert follow_up.history[0].role == "user"
    assert follow_up.history[0].content == "What is Adaptive RAG indexing?"
    assert follow_up.retrieval_query is not None
    assert "Adaptive RAG indexing" in follow_up.retrieval_query
    assert retrieval.requests[-1].query == follow_up.retrieval_query

    history_turns = audit.list_history_turns(
        project_id=project_id,
        session_id=first.session_id,
        limit=20,
    )
    roles = [role for role, _ in history_turns]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_multi_turn_stream_same_session_history_and_condense() -> None:
    """Stream path must continue session_id with history + condensed retrieval."""

    audit = InMemoryChatAuditWriter()
    runner = RecordingRunner()
    chunk_id = uuid4()
    retrieval = StaticRetrieval([_result(chunk_id, "stream multi-turn evidence")])
    service = ChatService(
        runner=runner,
        retrieval_service=retrieval,
        audit_writer=audit,
        query_condenser=DeterministicQueryCondenser(),
    )
    project_id = uuid4()

    first_events = list(
        service.stream(
            ChatRequest(
                project_id=project_id,
                message="What is Adaptive RAG indexing?",
            )
        )
    )
    first_final = next(event for event in first_events if event.event == "final")
    first_session_id = first_final.data["session_id"]
    assert first_session_id is not None

    second_events = list(
        service.stream(
            ChatRequest(
                project_id=project_id,
                session_id=UUID(first_session_id),
                message="Why does it matter?",
            )
        )
    )
    session_started = next(
        event for event in second_events if event.event == "session_started"
    )
    assert session_started.data["session_id"] == first_session_id
    second_final = next(event for event in second_events if event.event == "final")
    assert second_final.data["session_id"] == first_session_id

    assert len(runner.requests) == 2
    follow_up = runner.requests[1]
    assert len(follow_up.history) == 2
    assert follow_up.history[0].content == "What is Adaptive RAG indexing?"
    assert follow_up.retrieval_query is not None
    assert "Adaptive RAG indexing" in follow_up.retrieval_query
    assert retrieval.requests[-1].query == follow_up.retrieval_query

    history_turns = audit.list_history_turns(
        project_id=project_id,
        session_id=UUID(first_session_id),
        limit=20,
    )
    assert [role for role, _ in history_turns] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


def test_grounded_runner_uses_retrieval_query() -> None:
    chunk_id = uuid4()
    retrieval = StaticRetrieval([_result(chunk_id, "condensed hit")])
    runner = RetrievalGroundedChatRunner()
    tools = ChatTools(
        retrieval=ChatRetrievalTool(
            retrieval_service=retrieval,
            project_id=uuid4(),
            default_limit=5,
            default_metadata_filter=None,
        )
    )
    output = runner.run(
        ChatRunnerRequest(
            project_id=uuid4(),
            message="Why does it matter?",
            retrieval_limit=5,
            metadata_filter=None,
            retrieval_query="Adaptive RAG indexing — Why does it matter?",
        ),
        tools,
    )
    assert retrieval.requests[0].query == (
        "Adaptive RAG indexing — Why does it matter?"
    )
    assert "condensed hit" in output.answer


def test_deterministic_condenser_spanish_follow_up() -> None:
    condenser = DeterministicQueryCondenser()
    history = (
        ChatHistoryTurn(role="user", content="Cual es la politica de reembolsos?"),
        ChatHistoryTurn(role="assistant", content="Son 30 dias."),
    )
    query = condenser.condense(history=history, message="y cuento dias son?")
    assert "reembolsos" in query.lower() or "reembolsos" in query
    assert "cuento" in query.lower() or "dias" in query.lower()


def test_deterministic_condenser_short_confirmation_uses_assistant() -> None:
    condenser = DeterministicQueryCondenser()
    history = (
        ChatHistoryTurn(role="user", content="Puedes generar el reporte de costos?"),
        ChatHistoryTurn(
            role="assistant",
            content="Si quieres, genero el reporte de costos del proyecto.",
        ),
    )
    query = condenser.condense(history=history, message="dale")
    assert "reporte de costos" in query.lower()
    assert "dale" in query.lower()
