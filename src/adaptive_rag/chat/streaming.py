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
    "step",
    "tool_call",
    "answer_delta",
    "heartbeat",
    "final",
    "error",
]
type ChatStreamEventPayload = Mapping[str, object]
type ChatStepStatus = Literal["start", "done", "error"]


@dataclass(frozen=True, slots=True)
class ChatStreamEvent:
    """Evento de streaming listo para framing SSE."""

    event: ChatStreamEventName
    data: ChatStreamEventPayload


@dataclass(frozen=True, slots=True)
class ChatStepUsage:
    """Usage/costo serializable asociado a un step de chat."""

    slot: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    cost_source: str | None = None


@dataclass(frozen=True, slots=True)
class ChatStep:
    """Step de pipeline serializable para eventos y metadata de chat."""

    id: str
    status: ChatStepStatus
    elapsed_ms: int | None = None
    detail: Mapping[str, object] | None = None
    usage: ChatStepUsage | None = None


def chat_stream_session_started_event(session_id: UUID) -> ChatStreamEvent:
    return ChatStreamEvent(
        event="session_started",
        data={"session_id": str(session_id)},
    )


def chat_stream_step_event(step: ChatStep) -> ChatStreamEvent:
    return ChatStreamEvent(event="step", data=serialize_chat_step(step))


def serialize_chat_step(step: ChatStep) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": step.id,
        "status": step.status,
    }
    if step.elapsed_ms is not None:
        payload["elapsed_ms"] = step.elapsed_ms
    if step.detail is not None:
        payload["detail"] = dict(step.detail)
    if step.usage is not None:
        payload["usage"] = serialize_chat_step_usage(step.usage)
    return payload


def serialize_chat_step_usage(usage: ChatStepUsage) -> dict[str, object]:
    payload: dict[str, object] = {
        "slot": usage.slot,
        "provider": usage.provider,
        "model": usage.model,
    }
    if usage.input_tokens is not None:
        payload["input_tokens"] = usage.input_tokens
    if usage.output_tokens is not None:
        payload["output_tokens"] = usage.output_tokens
    if usage.total_tokens is not None:
        payload["total_tokens"] = usage.total_tokens
    if usage.estimated_cost_usd is not None:
        payload["estimated_cost_usd"] = usage.estimated_cost_usd
    if usage.cost_source is not None:
        payload["cost_source"] = usage.cost_source
    return payload


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
