"""Tests del contrato de eventos streaming de chat M16."""

from __future__ import annotations

from uuid import UUID

from adaptive_rag.chat import ChatResponse, ChatToolCall
from adaptive_rag.chat.payloads import serialize_chat_response
from adaptive_rag.chat.streaming import (
    chat_stream_answer_delta_event,
    chat_stream_error_event,
    chat_stream_final_event,
    chat_stream_heartbeat_event,
    chat_stream_session_started_event,
    chat_stream_tool_call_event,
    serialize_chat_stream_event,
)


def test_session_started_event_serializes_as_sse_frame() -> None:
    session_id = UUID("11111111-1111-4111-8111-111111111111")

    event = chat_stream_session_started_event(session_id)

    assert event.event == "session_started"
    assert event.data == {"session_id": str(session_id)}
    expected = (
        'event: session_started\ndata: {"session_id":'
        '"11111111-1111-4111-8111-111111111111"}\n\n'
    )
    assert serialize_chat_stream_event(event) == expected


def test_final_event_reuses_chat_response_payload_shape() -> None:
    session_id = UUID("22222222-2222-4222-8222-222222222222")
    response = ChatResponse(
        answer="Alpha is grounded.",
        citations=(),
        tool_calls=(
            ChatToolCall(
                name="retrieval.search",
                query="alpha",
                limit=2,
                result_count=1,
            ),
        ),
        session_id=session_id,
    )

    event = chat_stream_final_event(response)

    assert event.event == "final"
    assert event.data == serialize_chat_response(response)
    assert serialize_chat_stream_event(event) == (
        'event: final\ndata: {"answer":"Alpha is grounded.",'
        '"citations":[],"session_id":"22222222-2222-4222-8222-222222222222",'
        '"tool_calls":[{"limit":2,"name":"retrieval.search",'
        '"query":"alpha","result_count":1}]}\n\n'
    )


def test_progress_event_factories_produce_stable_payloads() -> None:
    tool_call = ChatToolCall(
        name="retrieval.search",
        query="alpha evidence",
        limit=5,
        result_count=3,
    )

    assert chat_stream_tool_call_event(tool_call).data == {
        "name": "retrieval.search",
        "query": "alpha evidence",
        "limit": 5,
        "result_count": 3,
    }
    assert chat_stream_answer_delta_event("line one\nline two").data == {
        "text": "line one\nline two",
    }
    assert chat_stream_heartbeat_event(elapsed_ms=1200).data == {
        "elapsed_ms": 1200,
    }
    assert chat_stream_error_event("runner failed").data == {
        "detail": "runner failed",
    }


def test_serializer_keeps_multiline_payload_text_inside_json_data() -> None:
    event = chat_stream_answer_delta_event("line one\nline two")

    assert (
        serialize_chat_stream_event(event)
        == 'event: answer_delta\ndata: {"text":"line one\\nline two"}\n\n'
    )
