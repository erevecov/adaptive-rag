"""Payloads serializables compartidos para chat/tool calling."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from adaptive_rag.chat.models import ChatResponse, ChatToolCall
from adaptive_rag.retrieval.payloads import RetrievalResultPayload


class ChatToolCallPayload(TypedDict):
    name: str
    query: NotRequired[str]
    limit: NotRequired[int]
    result_count: NotRequired[int]
    arguments: NotRequired[dict[str, Any]]
    result_summary: NotRequired[dict[str, Any]]


class ChatResponsePayload(TypedDict):
    answer: str
    citations: list[RetrievalResultPayload]
    tool_calls: list[ChatToolCallPayload]
    session_id: NotRequired[str]


def serialize_chat_response(response: ChatResponse) -> ChatResponsePayload:
    payload: ChatResponsePayload = {
        "answer": response.answer,
        "citations": list(response.citations),
        "tool_calls": [
            serialize_chat_tool_call(tool_call)
            for tool_call in response.tool_calls
        ],
    }
    if response.session_id is not None:
        payload["session_id"] = str(response.session_id)
    return payload


def serialize_chat_tool_call(tool_call: ChatToolCall) -> ChatToolCallPayload:
    payload: ChatToolCallPayload = {
        "name": tool_call.name,
    }
    if tool_call.query is not None:
        payload["query"] = tool_call.query
    if tool_call.limit is not None:
        payload["limit"] = tool_call.limit
    if tool_call.result_count is not None:
        payload["result_count"] = tool_call.result_count
    if tool_call.arguments:
        payload["arguments"] = dict(tool_call.arguments)
    if tool_call.result_summary:
        payload["result_summary"] = dict(tool_call.result_summary)
    return payload
