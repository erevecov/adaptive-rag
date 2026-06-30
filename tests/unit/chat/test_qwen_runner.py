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


class RecordingKnowledgeProposalTool:
    name = "commit_knowledge"
    approve_name = "approve_knowledge"
    cancel_name = "cancel_knowledge"
    refine_name = "refine_knowledge"

    def __init__(self) -> None:
        self.commits: list[tuple[str, str, str | None]] = []
        self.approvals: list[str] = []
        self.cancellations: list[str | None] = []
        self.refinements: list[tuple[str, str, str]] = []

    def commit(
        self,
        *,
        knowledge_text: str,
        scope: str = "message",
        draft_id: str | None = None,
    ):
        self.commits.append((knowledge_text, scope, draft_id))
        return {
            "draft_id": draft_id or "draft-33333333",
            "proposed_text": knowledge_text,
            "review_action": "approve",
            "scope": scope,
            "status": "draft",
        }

    def refine(
        self,
        *,
        draft_id: str,
        knowledge_text: str,
        scope: str = "message",
    ):
        self.refinements.append((draft_id, knowledge_text, scope))
        return {
            "draft_id": draft_id,
            "knowledge_lifecycle": {"action": "refine", "draft_id": draft_id},
            "proposed_text": knowledge_text,
            "review_action": "approve",
            "scope": scope,
            "status": "draft",
        }

    def cancel(self, *, draft_id: str | None = None):
        self.cancellations.append(draft_id)
        return {
            "draft_id": draft_id,
            "knowledge_lifecycle": {"action": "cancel", "draft_id": draft_id},
            "status": "cancelled",
        }

    def approve(self, *, draft_id: str):
        self.approvals.append(draft_id)
        return {
            "draft_id": draft_id,
            "knowledge_lifecycle": {"action": "approve", "draft_id": draft_id},
            "status": "approval_requested",
        }


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


def test_qwen_chat_runner_executes_commit_knowledge_tool_when_requested() -> None:
    project_id = uuid4()
    knowledge = RecordingKnowledgeProposalTool()
    client = RecordingChatClient(
        [
            _tool_call_response(
                {
                    "knowledge_text": "Document this deployment exception.",
                    "scope": "message",
                },
                name="commit_knowledge",
            ),
            _final_response(
                {
                    "answer": "Prepared a pending knowledge proposal.",
                    "cited_chunk_ids": [],
                }
            ),
        ]
    )

    output = QwenChatRunner(model_name="qwen-plus", client=client).run(
        ChatRunnerRequest(
            project_id=project_id,
            message="Propose this as knowledge: Document this deployment exception.",
            retrieval_limit=2,
            metadata_filter=None,
        ),
        _tools(
            project_id=project_id,
            retrieval=RecordingRetrievalService([]),
            default_limit=2,
            knowledge=knowledge,
        ),
    )

    assert knowledge.commits == [
        ("Document this deployment exception.", "message", None)
    ]
    tool_names = [
        tool["function"]["name"]
        for tool in client.requests[0]["tools"]
    ]
    assert tool_names == [
        "retrieval_search",
        "commit_knowledge",
        "refine_knowledge",
        "cancel_knowledge",
        "approve_knowledge",
    ]
    tool_message = client.requests[1]["messages"][-1]
    assert tool_message["role"] == "tool"
    assert json.loads(tool_message["content"]) == {
        "draft_id": "draft-33333333",
        "proposed_text": "Document this deployment exception.",
        "review_action": "approve",
        "scope": "message",
        "status": "draft",
    }
    assert output.answer == "Prepared a pending knowledge proposal."
    assert output.cited_chunk_ids == ()


def test_qwen_chat_runner_executes_knowledge_lifecycle_tools() -> None:
    project_id = uuid4()
    knowledge = RecordingKnowledgeProposalTool()
    client = RecordingChatClient(
        [
            _tool_call_response(
                {
                    "draft_id": "draft-33333333",
                    "knowledge_text": "Shorter deployment exception.",
                    "scope": "session",
                },
                name="refine_knowledge",
            ),
            _final_response({"answer": "Updated the draft.", "cited_chunk_ids": []}),
            _tool_call_response(
                {"draft_id": "draft-33333333"},
                name="approve_knowledge",
            ),
            _final_response({"answer": "Approved the draft.", "cited_chunk_ids": []}),
            _tool_call_response(
                {"draft_id": "draft-44444444"},
                name="cancel_knowledge",
            ),
            _final_response({"answer": "Cancelled the draft.", "cited_chunk_ids": []}),
        ]
    )
    tools = _tools(
        project_id=project_id,
        retrieval=RecordingRetrievalService([]),
        default_limit=2,
        knowledge=knowledge,
    )

    QwenChatRunner(model_name="qwen-plus", client=client).run(
        ChatRunnerRequest(
            project_id=project_id,
            message="Refine draft-33333333.",
            retrieval_limit=2,
            metadata_filter=None,
        ),
        tools,
    )
    QwenChatRunner(model_name="qwen-plus", client=client).run(
        ChatRunnerRequest(
            project_id=project_id,
            message="Approve draft-33333333.",
            retrieval_limit=2,
            metadata_filter=None,
        ),
        tools,
    )
    QwenChatRunner(model_name="qwen-plus", client=client).run(
        ChatRunnerRequest(
            project_id=project_id,
            message="Cancel draft-44444444.",
            retrieval_limit=2,
            metadata_filter=None,
        ),
        tools,
    )

    assert knowledge.refinements == [
        ("draft-33333333", "Shorter deployment exception.", "session")
    ]
    assert knowledge.approvals == ["draft-33333333"]
    assert knowledge.cancellations == ["draft-44444444"]


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
    knowledge: RecordingKnowledgeProposalTool | None = None,
) -> ChatTools:
    return ChatTools(
        retrieval=ChatRetrievalTool(
            retrieval_service=retrieval,
            project_id=project_id,
            default_limit=default_limit,
            default_metadata_filter=None,
        ),
        knowledge=knowledge,
    )


def _tool_call_response(
    arguments: dict[str, object],
    *,
    name: str = "retrieval_search",
) -> dict[str, Any]:
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
                                "name": name,
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
