"""Payloads serializables compartidos para chat/tool calling."""

from __future__ import annotations

from typing import TypedDict

from adaptive_rag.chat.models import ChatResponse, ChatToolCall
from adaptive_rag.retrieval.payloads import RetrievalResultPayload


class ChatToolCallPayload(TypedDict):
    name: str
    query: str
    limit: int
    result_count: int


class ChatResponsePayload(TypedDict):
    answer: str
    citations: list[RetrievalResultPayload]
    tool_calls: list[ChatToolCallPayload]


def serialize_chat_response(response: ChatResponse) -> ChatResponsePayload:
    return {
        "answer": response.answer,
        "citations": list(response.citations),
        "tool_calls": [
            serialize_chat_tool_call(tool_call)
            for tool_call in response.tool_calls
        ],
    }


def serialize_chat_tool_call(tool_call: ChatToolCall) -> ChatToolCallPayload:
    return {
        "name": tool_call.name,
        "query": tool_call.query,
        "limit": tool_call.limit,
        "result_count": tool_call.result_count,
    }
