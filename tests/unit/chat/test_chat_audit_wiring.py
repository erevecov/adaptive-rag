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
from adaptive_rag.provider_usage import ProviderCallRecord
from adaptive_rag.retrieval import (
    DenseRetrievalCitation,
    RetrievalMetadataFilter,
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


class NonChatErrorRunner:
    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        raise RuntimeError("provider exploded")


class RaisingProviderUsage:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> tuple[ProviderCallRecord, ...]:
        self.calls += 1
        raise RuntimeError("provider usage failed")


def test_chat_service_records_successful_session_tool_and_messages() -> None:
    project_id = uuid4()
    chunk_id = uuid4()
    metadata_filter = RetrievalMetadataFilter(source_type="markdown", tags=("docs",))
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
            metadata_filter=metadata_filter,
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
    assert len(tool_events) == 1
    assert tool_events[0]["event"] == "retrieval_tool"
    assert tool_events[0]["query"] == "alpha evidence"
    assert tool_events[0]["limit"] == 1
    assert tool_events[0]["strategy"] == "dense"
    assert tool_events[0]["fallback_reason"] is None
    assert tool_events[0]["result_count"] == 1
    assert tool_events[0]["chunk_ids"] == [str(chunk_id)]
    assert tool_events[0]["metadata_filter"] == {
        "source_type": "markdown",
        "tags": ["docs"],
    }
    assert isinstance(tool_events[0]["latency_ms"], int)
    assert tool_events[0]["latency_ms"] >= 0
    assert serialize_chat_response(response)["session_id"] == str(audit.session_id)


def test_chat_service_records_graph_retrieval_strategy_from_results() -> None:
    project_id = uuid4()
    chunk_id = uuid4()
    audit = InMemoryChatAuditWriter(session_id=uuid4())
    service = ChatService(
        runner=ToolCallingRunner(query="alpha evidence", cited_chunk_ids=(chunk_id,)),
        retrieval_service=RecordingRetrievalService(
            [
                _retrieval_result(
                    chunk_id=chunk_id,
                    snippet="Alpha evidence",
                    strategy="graph",
                )
            ]
        ),
        audit_writer=audit,
    )

    service.respond(ChatRequest(project_id=project_id, message="alpha"))

    tool_events = [
        event for event in audit.events if event["event"] == "retrieval_tool"
    ]
    assert tool_events[0]["strategy"] == "graph"


def test_chat_service_records_graph_fallback_reason_from_results() -> None:
    project_id = uuid4()
    chunk_id = uuid4()
    audit = InMemoryChatAuditWriter(session_id=uuid4())
    service = ChatService(
        runner=ToolCallingRunner(query="alpha evidence", cited_chunk_ids=(chunk_id,)),
        retrieval_service=RecordingRetrievalService(
            [
                _retrieval_result(
                    chunk_id=chunk_id,
                    snippet="Alpha evidence",
                    fallback_reason="graph_projection_pending_backfill",
                )
            ]
        ),
        audit_writer=audit,
    )

    service.respond(ChatRequest(project_id=project_id, message="alpha"))

    tool_events = [
        event for event in audit.events if event["event"] == "retrieval_tool"
    ]
    assert tool_events[0]["strategy"] == "dense"
    assert tool_events[0]["fallback_reason"] == "graph_projection_pending_backfill"


def test_successful_chat_ignores_provider_usage_failure_and_succeeds() -> None:
    project_id = uuid4()
    chunk_id = uuid4()
    audit = InMemoryChatAuditWriter(session_id=uuid4())
    provider_usage = RaisingProviderUsage()
    service = ChatService(
        runner=ToolCallingRunner(query="alpha evidence", cited_chunk_ids=(chunk_id,)),
        retrieval_service=RecordingRetrievalService(
            [_retrieval_result(chunk_id=chunk_id, snippet="Alpha evidence")]
        ),
        audit_writer=audit,
        provider_usage_records=provider_usage,
    )

    response = service.respond(
        ChatRequest(project_id=project_id, message="What supports alpha?")
    )

    assert response.answer == "Alpha is backed by retrieved evidence."
    assert audit.events[-1] == {"event": "succeed_session"}
    assert provider_usage.calls == 1


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


def test_runner_error_ignores_provider_usage_failure_and_preserves_error() -> None:
    project_id = uuid4()
    chunk_id = uuid4()
    audit = InMemoryChatAuditWriter(session_id=uuid4())
    provider_usage = RaisingProviderUsage()
    service = ChatService(
        runner=RaisingRunner(),
        retrieval_service=RecordingRetrievalService(
            [_retrieval_result(chunk_id=chunk_id, snippet="Alpha evidence")]
        ),
        audit_writer=audit,
        provider_usage_records=provider_usage,
    )

    with pytest.raises(ChatServiceError, match="runner failed"):
        service.respond(ChatRequest(project_id=project_id, message="alpha"))

    assert audit.events[-1] == {
        "event": "fail_session",
        "error_message": "runner failed",
    }
    assert provider_usage.calls == 1


def test_non_chat_service_error_after_session_start_records_failure() -> None:
    audit = InMemoryChatAuditWriter(session_id=uuid4())
    service = ChatService(
        runner=NonChatErrorRunner(),
        retrieval_service=RecordingRetrievalService([]),
        audit_writer=audit,
    )

    with pytest.raises(RuntimeError, match="provider exploded"):
        service.respond(ChatRequest(project_id=uuid4(), message="alpha"))

    assert audit.events[-1] == {
        "event": "fail_session",
        "error_message": "provider exploded",
    }


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


def test_invalid_retrieval_limit_does_not_start_audit_session() -> None:
    audit = InMemoryChatAuditWriter(session_id=uuid4())
    service = ChatService(
        runner=ToolCallingRunner(query="alpha", cited_chunk_ids=()),
        retrieval_service=RecordingRetrievalService([]),
        audit_writer=audit,
    )

    with pytest.raises(ChatServiceError, match="retrieval_limit must be positive"):
        service.respond(
            ChatRequest(project_id=uuid4(), message="alpha", retrieval_limit=0)
        )

    assert audit.events == []


def _retrieval_result(
    *,
    chunk_id: UUID,
    snippet: str,
    strategy: str = "dense",
    fallback_reason: str | None = None,
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
        strategy=strategy,
        fallback_reason=fallback_reason,
    )
