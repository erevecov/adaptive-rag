"""Tests del contrato compartido de chat/tool calling M5."""

from __future__ import annotations

import logging
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
from adaptive_rag.chat.service import MAX_CHAT_MESSAGE_CHARS
from adaptive_rag.chat.streaming import chat_stream_error_event
from adaptive_rag.chat.tools import ChatTools
from adaptive_rag.provider_usage import ProviderCallRecord, ProviderTokenUsage
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


class ProviderUsageSnapshot:
    def __init__(self, records: tuple[ProviderCallRecord, ...]) -> None:
        self.records = records
        self.calls = 0

    def __call__(self) -> tuple[ProviderCallRecord, ...]:
        self.calls += 1
        return self.records


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

    assert len(runner.requests) == 1
    assert runner.requests[0].project_id == project_id
    assert runner.requests[0].message == "What supports alpha?"
    assert runner.requests[0].retrieval_limit == 2
    assert runner.requests[0].metadata_filter == metadata_filter
    assert runner.requests[0].retrieval_query == "What supports alpha?"
    assert runner.requests[0].history == ()
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
    provider_usage = ProviderUsageSnapshot(
        (
            ProviderCallRecord(
                provider="qwen",
                model="qwen-plus",
                operation="chat",
                outcome="succeeded",
                duration_ms=3100,
                usage=ProviderTokenUsage(
                    input_tokens=120,
                    output_tokens=24,
                    total_tokens=144,
                ),
                usage_source="provider_reported",
                estimated_cost_usd=0.0012,
            ),
        )
    )

    events = list(
        ChatService(
            runner=runner,
            retrieval_service=retrieval,
            audit_writer=audit,
            provider_usage_records=provider_usage,
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
        "step",
        "step",
        "step",
        "step",
        "tool_call",
        "answer_delta",
        "final",
    ]
    assert events[0].data == {"session_id": str(session_id)}
    assert events[1].data["id"] == "answer"
    assert events[1].data["status"] == "start"
    assert events[2].data["id"] == "retrieval"
    assert events[2].data["status"] == "start"
    assert events[2].data["detail"]["limit"] == 2
    assert events[2].data["detail"]["query"] == "alpha evidence"
    assert events[2].data["detail"]["strategy"] == "dense_sparse"
    assert events[2].data["detail"]["route"] == "dense_sparse"
    assert events[3].data["id"] == "retrieval"
    assert events[3].data["status"] == "done"
    assert isinstance(events[3].data["elapsed_ms"], int)
    assert events[3].data["detail"] == {
        "limit": 2,
        "query": "alpha evidence",
        "result_count": 1,
        "strategy": "dense",
    }
    assert events[4].data["id"] == "answer"
    assert events[4].data["status"] == "done"
    assert events[4].data["usage"] == {
        "cost_source": "provider_reported",
        "estimated_cost_usd": 0.0012,
        "input_tokens": 120,
        "model": "qwen-plus",
        "output_tokens": 24,
        "provider": "qwen",
        "slot": "chat",
        "total_tokens": 144,
    }
    assert events[5].data == {
        "name": "retrieval.search",
        "query": "alpha evidence",
        "limit": 2,
        "result_count": 1,
    }
    assert events[6].data == {"text": "Alpha is backed by retrieved evidence."}
    assert events[7].data == {
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
    assistant_messages = [
        event
        for event in audit.events
        if event["event"] == "message" and event["role"] == "assistant"
    ]
    assert assistant_messages == [
        {
            "content": "Alpha is backed by retrieved evidence.",
            "event": "message",
            "metadata_json": {
                "steps": [
                    events[3].data,
                    events[4].data,
                ]
            },
            "role": "assistant",
        }
    ]
    assert provider_usage.calls == 1
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

    assert [event.event for event in events] == [
        "session_started",
        "step",
        "step",
        "error",
    ]
    assert events[1].data["id"] == "answer"
    assert events[1].data["status"] == "start"
    assert events[2].data["id"] == "answer"
    assert events[2].data["status"] == "error"
    assert events[2].data["detail"] == {
        "code": "chat_error",
        "error": "runner failed",
        "retryable": False,
    }
    assert events[3] == chat_stream_error_event("runner failed")
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
        (
            ChatRequest(
                project_id=uuid4(),
                message="x" * (MAX_CHAT_MESSAGE_CHARS + 1),
            ),
            f"message must be at most {MAX_CHAT_MESSAGE_CHARS} characters",
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


def test_chat_service_accepts_message_at_max_length() -> None:
    project_id = uuid4()
    runner = NoToolRunner()
    retrieval = RecordingRetrievalService([])
    message = "a" * MAX_CHAT_MESSAGE_CHARS

    ChatService(runner=runner, retrieval_service=retrieval).respond(
        ChatRequest(project_id=project_id, message=message)
    )

    assert len(runner.requests) == 1
    assert runner.requests[0].message == message


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


def test_chat_service_skips_citations_not_returned_by_retrieval(
    caplog: pytest.LogCaptureFixture,
) -> None:
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
        cited_chunk_ids=(unknown_chunk_id, retrieved_chunk_id, retrieved_chunk_id),
    )

    with caplog.at_level(logging.WARNING, logger="adaptive_rag.chat.service"):
        response = ChatService(runner=runner, retrieval_service=retrieval).respond(
            ChatRequest(project_id=project_id, message="What supports alpha?")
        )

    assert response.answer == "Alpha is backed by retrieved evidence."
    assert len(response.citations) == 1
    assert response.citations[0]["chunk_id"] == str(retrieved_chunk_id)
    assert any(
        record.getMessage() == "chat_citation_skipped_unknown"
        for record in caplog.records
    )


def test_chat_service_logs_provider_usage_audit_failure_with_exc_info(
    caplog: pytest.LogCaptureFixture,
) -> None:
    project_id = uuid4()
    chunk_id = uuid4()
    retrieval = RecordingRetrievalService(
        [_retrieval_result(chunk_id=chunk_id, snippet="Alpha original evidence")]
    )
    runner = ToolCallingRunner(
        retrieval_query="alpha evidence",
        cited_chunk_ids=(chunk_id,),
    )
    audit = InMemoryChatAuditWriter(session_id=uuid4())

    def _raise_usage() -> tuple[ProviderCallRecord, ...]:
        raise RuntimeError("usage source unavailable")

    with caplog.at_level(logging.WARNING, logger="adaptive_rag.chat.service"):
        response = ChatService(
            runner=runner,
            retrieval_service=retrieval,
            audit_writer=audit,
            provider_usage_records=_raise_usage,
        ).respond(ChatRequest(project_id=project_id, message="What supports alpha?"))

    assert response.answer == "Alpha is backed by retrieved evidence."
    warnings = [
        record
        for record in caplog.records
        if record.getMessage() == "chat_provider_usage_audit_failed"
    ]
    assert warnings
    assert all(record.exc_info is not None for record in warnings)
    assert any(
        record.exc_info is not None and record.exc_info[0] is RuntimeError
        for record in warnings
    )
    assert audit.events[-1] == {"event": "succeed_session"}


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

def test_chat_service_stream_emits_heartbeats_while_runner_blocks() -> None:
    import adaptive_rag.chat.service as service_module
    from time import sleep

    class SlowRunner:
        def run(self, request, tools, **kwargs):  # noqa: ANN001
            sleep(0.35)
            return ChatRunnerOutput(answer="slow ok", cited_chunk_ids=())

    old = service_module._STREAM_HEARTBEAT_SECONDS
    service_module._STREAM_HEARTBEAT_SECONDS = 0.08
    try:
        events = list(
            ChatService(
                runner=SlowRunner(),
                retrieval_service=RecordingRetrievalService([]),
                audit_writer=InMemoryChatAuditWriter(session_id=uuid4()),
            ).stream(ChatRequest(project_id=uuid4(), message="hello"))
        )
    finally:
        service_module._STREAM_HEARTBEAT_SECONDS = old

    names = [event.event for event in events]
    assert names[0] == "session_started"
    assert "heartbeat" in names
    assert names[-1] == "final"


def test_chat_service_stream_close_fails_session_as_client_disconnected() -> None:
    """Closing the stream generator mid-flight must fail_session promptly."""

    from time import sleep

    class SlowRunner:
        def run(self, request, tools, **kwargs):  # noqa: ANN001
            sleep(1.5)
            return ChatRunnerOutput(answer="should not finish", cited_chunk_ids=())

    audit = InMemoryChatAuditWriter(session_id=uuid4())
    stream = ChatService(
        runner=SlowRunner(),
        retrieval_service=RecordingRetrievalService([]),
        audit_writer=audit,
    ).stream(ChatRequest(project_id=uuid4(), message="cancel me"))

    assert next(stream).event == "session_started"
    assert next(stream).event == "step"  # answer start
    stream.close()

    assert any(
        event.get("event") == "cancel_session"
        and event.get("error_message") == "client_disconnected"
        for event in audit.events
    )


def test_chat_service_stream_emits_retrieval_steps_before_answer_deltas() -> None:
    """Retrieval step start/done must interleave before final answer deltas."""

    from time import sleep

    chunk_id = uuid4()
    retrieval = RecordingRetrievalService(
        [_retrieval_result(chunk_id=chunk_id, snippet="live step evidence")]
    )

    class RetrievalThenStreamRunner:
        def run(self, request, tools, **kwargs):  # noqa: ANN001
            tools.retrieval.search(query="live step query", limit=2)
            # Keep the worker alive briefly so the main loop can drain steps
            # before the answer_delta sink runs.
            sleep(0.05)
            on_delta = kwargs.get("on_answer_delta")
            if on_delta is not None:
                on_delta("Live ")
                on_delta("answer.")
            return ChatRunnerOutput(
                answer="Live answer.",
                cited_chunk_ids=(chunk_id,),
            )

    events = list(
        ChatService(
            runner=RetrievalThenStreamRunner(),
            retrieval_service=retrieval,
            audit_writer=InMemoryChatAuditWriter(session_id=uuid4()),
        ).stream(
            ChatRequest(
                project_id=uuid4(),
                message="What is live?",
                retrieval_limit=2,
            )
        )
    )

    names = [event.event for event in events]
    first_retrieval = next(
        i
        for i, event in enumerate(events)
        if event.event == "step" and event.data.get("id") == "retrieval"
    )
    first_delta = names.index("answer_delta")
    assert first_retrieval < first_delta
    assert events[first_retrieval].data["status"] == "start"
    retrieval_done = next(
        event
        for event in events
        if event.event == "step"
        and event.data.get("id") == "retrieval"
        and event.data.get("status") == "done"
    )
    assert retrieval_done.data["detail"]["result_count"] == 1
