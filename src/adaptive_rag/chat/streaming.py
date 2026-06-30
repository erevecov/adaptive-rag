"""Eventos SSE serializables para streaming de chat."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from adaptive_rag.chat.models import ChatResponse, ChatToolCall
from adaptive_rag.chat.payloads import (
    ChatResponsePayload,
    serialize_chat_response,
    serialize_chat_tool_call,
)

type ChatStreamEventName = Literal[
    "session_started",
    "tool_call",
    "answer_delta",
    "heartbeat",
    "final",
    "error",
]
type ChatStreamEventPayload = Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ChatStreamEvent:
    """Evento de streaming listo para framing SSE."""

    event: ChatStreamEventName
    data: ChatStreamEventPayload


def chat_stream_session_started_event(session_id: UUID) -> ChatStreamEvent:
    return ChatStreamEvent(
        event="session_started",
        data={"session_id": str(session_id)},
    )


def chat_stream_tool_call_event(tool_call: ChatToolCall) -> ChatStreamEvent:
    return ChatStreamEvent(
        event="tool_call",
        data=serialize_chat_tool_call(tool_call),
    )


def chat_stream_answer_delta_event(text: str) -> ChatStreamEvent:
    return ChatStreamEvent(event="answer_delta", data={"text": text})


def chat_stream_heartbeat_event(*, elapsed_ms: int) -> ChatStreamEvent:
    return ChatStreamEvent(event="heartbeat", data={"elapsed_ms": elapsed_ms})


def chat_stream_final_event(response: ChatResponse) -> ChatStreamEvent:
    payload: ChatResponsePayload = serialize_chat_response(response)
    return ChatStreamEvent(event="final", data=payload)


def chat_stream_error_event(detail: str) -> ChatStreamEvent:
    return ChatStreamEvent(event="error", data={"detail": detail})


def serialize_chat_stream_event(event: ChatStreamEvent) -> str:
    """Serializa un evento con framing SSE y JSON deterministico."""

    data = json.dumps(
        event.data,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"event: {event.event}\ndata: {data}\n\n"
