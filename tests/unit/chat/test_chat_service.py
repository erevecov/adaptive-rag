"""Tests del contrato compartido de chat/tool calling M5."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from adaptive_rag.chat import (
    ChatRequest,
    ChatRunnerOutput,
    ChatRunnerRequest,
    ChatService,
    ChatServiceError,
    ChatToolCall,
)
from adaptive_rag.chat.audit import InMemoryChatAuditWriter
from adaptive_rag.chat.payloads import serialize_chat_response
from adaptive_rag.chat.streaming import chat_stream_error_event
from adaptive_rag.chat.tools import ChatTools
from adaptive_rag.retrieval import (
    DenseRetrievalCitation,
    RetrievalMetadataFilter,
    RetrievalRerankOptions,
    RetrievalSearchRequest,
    RetrievalSearchResult,
    RetrievalServiceError,
)
from adaptive_rag.retrieval.payloads import serialize_retrieval_result


class RecordingRetrievalService:
    def __init__(self, results: list[RetrievalSearchResult]) -> None:
        self.results = results
        self.requests: list[RetrievalSearchRequest] = []

    def search(
        self,
        request: RetrievalSearchRequest,
    ) -> list[RetrievalSearchResult]:
        self.requests.append(request)
        return list(self.results)


class RaisingRetrievalService:
    def __init__(self, message: str) -> None:
        self.message = message
        self.requests: list[RetrievalSearchRequest] = []

    def search(
        self,
        request: RetrievalSearchRequest,
    ) -> list[RetrievalSearchResult]:
        self.requests.append(request)
        raise RetrievalServiceError(self.message)


class ToolCallingRunner:
    def __init__(
        self,
        *,
        retrieval_query: str,
        cited_chunk_ids: tuple[UUID, ...],
    ) -> None:
        self.retrieval_query = retrieval_query
        self.cited_chunk_ids = cited_chunk_ids
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
        assert result.results
        return ChatRunnerOutput(
            answer="Alpha is backed by retrieved evidence.",
            cited_chunk_ids=self.cited_chunk_ids,
        )


class NoToolRunner:
    def __init__(self) -> None:
        self.requests: list[ChatRunnerRequest] = []

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        self.requests.append(request)
        return ChatRunnerOutput(
            answer="No retrieval was needed.",
            cited_chunk_ids=(),
        )


class RaisingRunner:
    def __init__(self, message: str = "runner failed") -> None:
        self.message = message
        self.requests: list[ChatRunnerRequest] = []

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        self.requests.append(request)
        raise ChatServiceError(self.message)


def test_chat_service_runs_retrieval_tool_and_returns_cited_payloads() -> None:
    project_id = uuid4()
    chunk_id = uuid4()
    metadata_filter = RetrievalMetadataFilter(source_type="markdown", tags=("docs",))
    retrieval_result = _retrieval_result(
        chunk_id=chunk_id,
        snippet="Alpha original evidence",
    )
    retrieval = RecordingRetrievalService([retrieval_result])
    runner = ToolCallingRunner(
        retrieval_query="alpha evidence",
        cited_chunk_ids=(chunk_id,),
    )

    response = ChatService(
        runner=runner,
        retrieval_service=retrieval,
    ).respond(
        ChatRequest(
            project_id=project_id,
            message="What supports alpha?",
            retrieval_limit=2,
            metadata_filter=metadata_filter,
        )
    )

    assert runner.requests == [
        ChatRunnerRequest(
            project_id=project_id,
            message="What supports alpha?",
            retrieval_limit=2,
            metadata_filter=metadata_filter,
        )
    ]
    assert retrieval.requests == [
        RetrievalSearchRequest(
            project_id=project_id,
            query="alpha evidence",
            limit=2,
            metadata_filter=metadata_filter,
        )
    ]
    assert response.answer == "Alpha is backed by retrieved evidence."
    assert [item["chunk_id"] for item in response.citations] == [str(chunk_id)]
    assert response.citations[0]["citation"]["snippet"] == "Alpha original evidence"
    assert response.tool_calls == (
        ChatToolCall(
            name="retrieval.search",
            query="alpha evidence",
            limit=2,
            result_count=1,
        ),
    )
    assert serialize_chat_response(response) == {
        "answer": "Alpha is backed by retrieved evidence.",
        "citations": list(response.citations),
        "tool_calls": [
            {
                "name": "retrieval.search",
                "query": "alpha evidence",
                "limit": 2,
                "result_count": 1,
            }
        ],
    }


def test_chat_service_passes_rerank_options_to_retrieval_tool() -> None:
    project_id = uuid4()
    chunk_id = uuid4()
    retrieval = RecordingRetrievalService(
        [_retrieval_result(chunk_id=chunk_id, snippet="Alpha original evidence")]
    )
    runner = ToolCallingRunner(
        retrieval_query="alpha evidence",
        cited_chunk_ids=(chunk_id,),
    )

    ChatService(runner=runner, retrieval_service=retrieval).respond(
        ChatRequest(
            project_id=project_id,
            message="What supports alpha?",
            retrieval_limit=3,
            rerank_enabled=True,
            rerank_candidate_limit=10,
        )
    )

    assert retrieval.requests == [
        RetrievalSearchRequest(
            project_id=project_id,
            query="alpha evidence",
            limit=3,
            metadata_filter=None,
            rerank=RetrievalRerankOptions(candidate_limit=10),
            strategy="dense_sparse",
        )
    ]


def test_chat_service_can_answer_without_retrieval_tool_call() -> None:
    project_id = uuid4()
    retrieval = RecordingRetrievalService([])
    runner = NoToolRunner()

    response = ChatService(
        runner=runner,
        retrieval_service=retrieval,
    ).respond(
        ChatRequest(
            project_id=project_id,
            message="Say hello.",
        )
    )

    assert len(runner.requests) == 1
    assert retrieval.requests == []
    assert response.answer == "No retrieval was needed."
    assert response.citations == ()
    assert response.tool_calls == ()


def test_chat_service_streams_session_tool_delta_and_final_events() -> None:
    project_id = uuid4()
    chunk_id = uuid4()
    session_id = uuid4()
    retrieval_result = _retrieval_result(
        chunk_id=chunk_id,
        snippet="Alpha original evidence",
    )
    retrieval = RecordingRetrievalService([retrieval_result])
    runner = ToolCallingRunner(
        retrieval_query="alpha evidence",
        cited_chunk_ids=(chunk_id,),
    )
    audit = InMemoryChatAuditWriter(session_id=session_id)

    events = list(
        ChatService(
            runner=runner,
            retrieval_service=retrieval,
            audit_writer=audit,
        ).stream(
            ChatRequest(
                project_id=project_id,
                message="What supports alpha?",
                retrieval_limit=2,
            )
        )
    )

    assert [event.event for event in events] == [
        "session_started",
        "tool_call",
        "answer_delta",
        "final",
    ]
    assert events[0].data == {"session_id": str(session_id)}
    assert events[1].data == {
        "name": "retrieval.search",
        "query": "alpha evidence",
        "limit": 2,
        "result_count": 1,
    }
    assert events[2].data == {"text": "Alpha is backed by retrieved evidence."}
    assert events[3].data == {
        "answer": "Alpha is backed by retrieved evidence.",
        "citations": [serialize_retrieval_result(retrieval_result)],
        "tool_calls": [
            {
                "name": "retrieval.search",
                "query": "alpha evidence",
                "limit": 2,
                "result_count": 1,
            }
        ],
        "session_id": str(session_id),
    }
    assert {
        "event": "message",
        "role": "assistant",
        "content": "Alpha is backed by retrieved evidence.",
    } in audit.events
    assert audit.events[-1] == {"event": "succeed_session"}


def test_chat_service_stream_rejects_invalid_requests_before_session_start() -> None:
    audit = InMemoryChatAuditWriter(session_id=uuid4())
    runner = NoToolRunner()
    retrieval = RecordingRetrievalService([])

    with pytest.raises(ChatServiceError, match="message must not be empty"):
        list(
            ChatService(
                runner=runner,
                retrieval_service=retrieval,
                audit_writer=audit,
            ).stream(ChatRequest(project_id=uuid4(), message=" "))
        )

    assert runner.requests == []
    assert retrieval.requests == []
    assert audit.events == []


def test_chat_service_stream_yields_error_event_after_session_failure() -> None:
    audit = InMemoryChatAuditWriter(session_id=uuid4())

    events = list(
        ChatService(
            runner=RaisingRunner("runner failed"),
            retrieval_service=RecordingRetrievalService([]),
            audit_writer=audit,
        ).stream(ChatRequest(project_id=uuid4(), message="alpha"))
    )

    assert [event.event for event in events] == ["session_started", "error"]
    assert events[1] == chat_stream_error_event("runner failed")
    assert audit.events[-1] == {
        "event": "fail_session",
        "error_message": "runner failed",
    }


@pytest.mark.parametrize(
    ("chat_request", "message"),
    [
        (
            ChatRequest(project_id=uuid4(), message=" "),
            "message must not be empty",
        ),
        (
            ChatRequest(project_id=uuid4(), message="hello", retrieval_limit=0),
            "retrieval_limit must be positive",
        ),
        (
            ChatRequest(project_id=uuid4(), message="hello", retrieval_limit=51),
            "retrieval_limit must be between 1 and 50",
        ),
        (
            ChatRequest(
                project_id=uuid4(),
                message="hello",
                retrieval_limit=11,
                rerank_enabled=True,
                rerank_candidate_limit=10,
            ),
            "rerank_candidate_limit must be greater than or equal to retrieval_limit",
        ),
    ],
)
def test_chat_service_rejects_invalid_requests_without_runner_or_retrieval_call(
    chat_request: ChatRequest,
    message: str,
) -> None:
    retrieval = RecordingRetrievalService([])
    runner = NoToolRunner()

    with pytest.raises(ChatServiceError, match=message):
        ChatService(runner=runner, retrieval_service=retrieval).respond(chat_request)

    assert runner.requests == []
    assert retrieval.requests == []


def test_chat_service_maps_retrieval_errors_to_chat_errors() -> None:
    project_id = uuid4()
    retrieval = RaisingRetrievalService("source_type must not be empty")
    runner = ToolCallingRunner(
        retrieval_query="alpha evidence",
        cited_chunk_ids=(),
    )

    with pytest.raises(ChatServiceError, match="source_type must not be empty"):
        ChatService(runner=runner, retrieval_service=retrieval).respond(
            ChatRequest(project_id=project_id, message="What supports alpha?")
        )

    assert len(runner.requests) == 1
    assert len(retrieval.requests) == 1


def test_chat_service_rejects_citations_not_returned_by_retrieval() -> None:
    project_id = uuid4()
    retrieved_chunk_id = uuid4()
    unknown_chunk_id = uuid4()
    retrieval = RecordingRetrievalService(
        [
            _retrieval_result(
                chunk_id=retrieved_chunk_id,
                snippet="Alpha original evidence",
            )
        ]
    )
    runner = ToolCallingRunner(
        retrieval_query="alpha evidence",
        cited_chunk_ids=(unknown_chunk_id,),
    )

    with pytest.raises(ChatServiceError, match="citation .* was not returned"):
        ChatService(runner=runner, retrieval_service=retrieval).respond(
            ChatRequest(project_id=project_id, message="What supports alpha?")
        )


def _retrieval_result(
    *,
    chunk_id: UUID,
    snippet: str,
) -> RetrievalSearchResult:
    source_id = uuid4()
    document_id = uuid4()
    document_version_id = uuid4()
    citation = DenseRetrievalCitation(
        source_id=source_id,
        source_type="markdown",
        source_external_id="alpha.md",
        source_tags=("docs",),
        source_extra_metadata={"title": "Alpha"},
        document_id=document_id,
        document_stable_id="alpha-doc",
        document_version_id=document_version_id,
        document_version_number=1,
        chunk_id=chunk_id,
        char_start=0,
        char_end=len(snippet),
        snippet=snippet,
        section_metadata={"heading": "Alpha"},
    )
    return RetrievalSearchResult(
        chunk_id=chunk_id,
        distance=0.2,
        score=1 / 1.2,
        citation=citation,
        embedding_metadata={"provider": "fake"},
    )
