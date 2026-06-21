"""Tests de wiring audit trail en ChatService."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from adaptive_rag.chat import (
    ChatRequest,
    ChatRunnerOutput,
    ChatRunnerRequest,
    ChatService,
    ChatServiceError,
)
from adaptive_rag.chat.audit import InMemoryChatAuditWriter
from adaptive_rag.chat.payloads import serialize_chat_response
from adaptive_rag.chat.tools import ChatTools
from adaptive_rag.retrieval import (
    DenseRetrievalCitation,
    RetrievalSearchRequest,
    RetrievalSearchResult,
)


class RecordingRetrievalService:
    def __init__(self, results: list[RetrievalSearchResult]) -> None:
        self.results = results
        self.requests: list[RetrievalSearchRequest] = []

    def search(self, request: RetrievalSearchRequest) -> list[RetrievalSearchResult]:
        self.requests.append(request)
        return list(self.results)


class ToolCallingRunner:
    def __init__(self, *, query: str, cited_chunk_ids: tuple[UUID, ...]) -> None:
        self.query = query
        self.cited_chunk_ids = cited_chunk_ids

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        tools.retrieval.search(query=self.query, limit=request.retrieval_limit)
        return ChatRunnerOutput(
            answer="Alpha is backed by retrieved evidence.",
            cited_chunk_ids=self.cited_chunk_ids,
        )


class RaisingRunner:
    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        tools.retrieval.search(query=request.message, limit=request.retrieval_limit)
        raise ChatServiceError("runner failed")


def test_chat_service_records_successful_session_tool_and_messages() -> None:
    project_id = uuid4()
    chunk_id = uuid4()
    audit = InMemoryChatAuditWriter(session_id=uuid4())
    service = ChatService(
        runner=ToolCallingRunner(query="alpha evidence", cited_chunk_ids=(chunk_id,)),
        retrieval_service=RecordingRetrievalService(
            [_retrieval_result(chunk_id=chunk_id, snippet="Alpha evidence")]
        ),
        audit_writer=audit,
    )

    response = service.respond(
        ChatRequest(
            project_id=project_id,
            message="What supports alpha?",
            retrieval_limit=1,
        )
    )

    assert response.session_id == audit.session_id
    assert audit.events[0] == {
        "event": "start_session",
        "project_id": str(project_id),
        "message": "What supports alpha?",
        "retrieval_limit": 1,
    }
    assert {
        "event": "message",
        "role": "user",
        "content": "What supports alpha?",
    } in audit.events
    assert {
        "event": "message",
        "role": "assistant",
        "content": response.answer,
    } in audit.events
    assert audit.events[-1] == {"event": "succeed_session"}
    tool_events = [
        event for event in audit.events if event["event"] == "retrieval_tool"
    ]
    assert tool_events == [
        {
            "event": "retrieval_tool",
            "query": "alpha evidence",
            "limit": 1,
            "result_count": 1,
            "chunk_ids": [str(chunk_id)],
        }
    ]
    assert serialize_chat_response(response)["session_id"] == str(audit.session_id)


def test_chat_service_records_failed_session_after_runner_error() -> None:
    project_id = uuid4()
    chunk_id = uuid4()
    audit = InMemoryChatAuditWriter(session_id=uuid4())
    service = ChatService(
        runner=RaisingRunner(),
        retrieval_service=RecordingRetrievalService(
            [_retrieval_result(chunk_id=chunk_id, snippet="Alpha evidence")]
        ),
        audit_writer=audit,
    )

    with pytest.raises(ChatServiceError, match="runner failed"):
        service.respond(ChatRequest(project_id=project_id, message="alpha"))

    assert audit.events[-1] == {
        "event": "fail_session",
        "error_message": "runner failed",
    }
    assert any(event["event"] == "retrieval_tool" for event in audit.events)


def test_invalid_request_does_not_start_audit_session() -> None:
    audit = InMemoryChatAuditWriter(session_id=uuid4())
    service = ChatService(
        runner=ToolCallingRunner(query="alpha", cited_chunk_ids=()),
        retrieval_service=RecordingRetrievalService([]),
        audit_writer=audit,
    )

    with pytest.raises(ChatServiceError, match="message must not be empty"):
        service.respond(ChatRequest(project_id=uuid4(), message=" "))

    assert audit.events == []


def _retrieval_result(*, chunk_id: UUID, snippet: str) -> RetrievalSearchResult:
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
