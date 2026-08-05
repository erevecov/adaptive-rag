"""Chat answer output filter redacts secrets on respond + stream."""

from __future__ import annotations

from uuid import uuid4

from adaptive_rag.chat import ChatRequest, ChatService
from adaptive_rag.chat.models import ChatRunnerOutput, ChatRunnerRequest
from adaptive_rag.chat.streaming import serialize_chat_stream_event
from adaptive_rag.chat.tools import ChatTools
from adaptive_rag.security.secrets import REDACTION_MARKER


class _LeakyRunner:
    def run(self, request: ChatRunnerRequest, tools: ChatTools) -> ChatRunnerOutput:
        del request, tools
        return ChatRunnerOutput(
            answer=(
                "Use this key sk-proj-abcdefghijklmnopqrstuvwxyz012345 for demos."
            ),
            cited_chunk_ids=(),
        )


class _EmptyRetrieval:
    def search(self, **kwargs):  # type: ignore[no-untyped-def]
        del kwargs

        class _Result:
            results: list = []

        return _Result()


def test_respond_redacts_secret_in_answer() -> None:
    service = ChatService(runner=_LeakyRunner(), retrieval_service=_EmptyRetrieval())
    response = service.respond(
        ChatRequest(project_id=uuid4(), message="What is the key?")
    )
    assert "sk-proj-" not in response.answer
    assert REDACTION_MARKER in response.answer


def test_stream_redacts_secret_in_answer_delta() -> None:
    service = ChatService(runner=_LeakyRunner(), retrieval_service=_EmptyRetrieval())
    events = list(
        service.stream(ChatRequest(project_id=uuid4(), message="leak please"))
    )
    payload = "\n".join(serialize_chat_stream_event(event) for event in events)
    assert "sk-proj-" not in payload
    assert REDACTION_MARKER in payload
    assert any(event.event == "answer_delta" for event in events)
