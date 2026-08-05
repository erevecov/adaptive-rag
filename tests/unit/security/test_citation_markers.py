"""Beflow-parity: fabricated [doc-N] markers are stripped from answers."""

from __future__ import annotations

from uuid import uuid4

from adaptive_rag.chat import ChatRequest, ChatService
from adaptive_rag.chat.models import ChatRunnerOutput, ChatRunnerRequest
from adaptive_rag.chat.streaming import serialize_chat_stream_event
from adaptive_rag.chat.tools import ChatTools
from adaptive_rag.security.citation_markers import (
    CitationMarkerFilter,
    filter_citation_markers,
)


def test_filter_drops_fabricated_doc_marker() -> None:
    text, fabricated = filter_citation_markers(
        "Claim [doc-1] is fine but [doc-9] is not.",
        max_doc=1,
    )
    assert "[doc-1]" in text
    assert "[doc-9]" not in text
    assert any("doc-9" in item for item in fabricated)


def test_filter_rewrites_decorated_valid_marker() -> None:
    text, fabricated = filter_citation_markers(
        "See [doc-1 (story-99)] for detail.",
        max_doc=1,
    )
    assert "[doc-1]" in text
    assert "story-99" not in text
    assert fabricated


def test_streaming_filter_handles_split_markers() -> None:
    filt = CitationMarkerFilter(max_doc=1)
    out = filt.push("Prefix [doc-")
    out += filt.push("2] suffix")
    out += filt.flush()
    assert "[doc-2]" not in out
    assert "Prefix" in out and "suffix" in out


class _MarkerRunner:
    def run(self, request: ChatRunnerRequest, tools: ChatTools) -> ChatRunnerOutput:
        del request, tools
        return ChatRunnerOutput(
            answer=(
                "Grounded [doc-1] then fake [doc-7] and "
                "sk-proj-abcdefghijklmnopqrstuvwxyz012345"
            ),
            cited_chunk_ids=(),
        )


class _EmptyRetrieval:
    def search(self, **kwargs):  # type: ignore[no-untyped-def]
        del kwargs

        class _Result:
            results: list = []

        return _Result()


def test_chat_service_strips_fabricated_markers_and_secrets() -> None:
    service = ChatService(runner=_MarkerRunner(), retrieval_service=_EmptyRetrieval())
    response = service.respond(
        ChatRequest(project_id=uuid4(), message="summarize")
    )
    # max_doc=0 when no structured citations → all doc markers dropped
    assert "[doc-1]" not in response.answer
    assert "[doc-7]" not in response.answer
    assert "sk-proj-" not in response.answer


def test_stream_strips_fabricated_markers() -> None:
    service = ChatService(runner=_MarkerRunner(), retrieval_service=_EmptyRetrieval())
    events = list(
        service.stream(ChatRequest(project_id=uuid4(), message="stream"))
    )
    payload = "\n".join(serialize_chat_stream_event(event) for event in events)
    assert "[doc-7]" not in payload
    assert "sk-proj-" not in payload
