from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

import pytest

from adaptive_rag.chat import ChatRunnerRequest
from adaptive_rag.chat.qwen import QwenChatRunner, QwenChatRunnerError
from adaptive_rag.chat.tools import ChatRetrievalTool, ChatTools
from adaptive_rag.retrieval import (
    DenseRetrievalCitation,
    RetrievalSearchRequest,
    RetrievalSearchResult,
)


class RecordingChatClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    def create_chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self.requests.append(
            {
                "model": model,
                "messages": messages,
                "tools": tools,
            }
        )
        return self.responses.pop(0)


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


def test_qwen_chat_runner_executes_retrieval_tool_and_returns_citations() -> None:
    project_id = uuid4()
    chunk_id = uuid4()
    retrieval = RecordingRetrievalService(
        [_retrieval_result(chunk_id=chunk_id, snippet="Alpha smoke evidence")]
    )
    client = RecordingChatClient(
        [
            _tool_call_response({"query": "alpha evidence", "limit": 5}),
            _final_response(
                {
                    "answer": "Alpha answer",
                    "cited_chunk_ids": [str(chunk_id)],
                }
            ),
        ]
    )

    output = QwenChatRunner(model_name="qwen-plus", client=client).run(
        ChatRunnerRequest(
            project_id=project_id,
            message="What supports alpha?",
            retrieval_limit=2,
            metadata_filter=None,
        ),
        _tools(project_id=project_id, retrieval=retrieval, default_limit=2),
    )

    assert retrieval.requests == [
        RetrievalSearchRequest(
            project_id=project_id,
            query="alpha evidence",
            limit=2,
            metadata_filter=None,
        )
    ]
    assert output.answer == "Alpha answer"
    assert output.cited_chunk_ids == (chunk_id,)
    assert len(client.requests) == 2
    assert client.requests[0]["model"] == "qwen-plus"
    assert client.requests[0]["tools"][0]["function"]["name"] == "retrieval_search"
    tool_message = client.requests[1]["messages"][-1]
    assert tool_message["role"] == "tool"
    assert json.loads(tool_message["content"])["results"][0]["chunk_id"] == str(
        chunk_id
    )


def test_qwen_chat_runner_rejects_non_json_final_response() -> None:
    project_id = uuid4()
    client = RecordingChatClient([_final_response("plain text")])

    with pytest.raises(
        QwenChatRunnerError,
        match="qwen chat response content must be a JSON object",
    ):
        QwenChatRunner(model_name="qwen-plus", client=client).run(
            ChatRunnerRequest(
                project_id=project_id,
                message="What supports alpha?",
                retrieval_limit=2,
                metadata_filter=None,
            ),
            _tools(
                project_id=project_id,
                retrieval=RecordingRetrievalService([]),
                default_limit=2,
            ),
        )


def _tools(
    *,
    project_id: UUID,
    retrieval: RecordingRetrievalService,
    default_limit: int,
) -> ChatTools:
    return ChatTools(
        retrieval=ChatRetrievalTool(
            retrieval_service=retrieval,
            project_id=project_id,
            default_limit=default_limit,
            default_metadata_filter=None,
        )
    )


def _tool_call_response(arguments: dict[str, object]) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_retrieval",
                            "type": "function",
                            "function": {
                            "name": "retrieval_search",
                                "arguments": json.dumps(arguments),
                            },
                        }
                    ],
                }
            }
        ]
    }


def _final_response(content: object) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": (
                        json.dumps(content) if not isinstance(content, str) else content
                    ),
                }
            }
        ]
    }


def _retrieval_result(
    *,
    chunk_id: UUID,
    snippet: str,
) -> RetrievalSearchResult:
    citation = DenseRetrievalCitation(
        source_id=uuid4(),
        source_type="markdown",
        source_external_id="alpha.md",
        source_tags=("docs",),
        source_extra_metadata={"title": "Alpha"},
        document_id=uuid4(),
        document_stable_id="alpha-doc",
        document_version_id=uuid4(),
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
        embedding_metadata=None,
    )
