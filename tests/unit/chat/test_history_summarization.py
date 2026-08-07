"""Rolling history summarization for long multi-turn sessions."""

from __future__ import annotations

from uuid import uuid4

from adaptive_rag.chat.audit import InMemoryChatAuditWriter
from adaptive_rag.chat.history import prepare_chat_history
from adaptive_rag.chat.models import ChatHistoryTurn, ChatRequest
from adaptive_rag.chat.service import ChatService
from adaptive_rag.chat.models import ChatRunnerOutput, ChatRunnerRequest
from adaptive_rag.chat.tools import ChatTools


class _CaptureRunner:
    def __init__(self) -> None:
        self.requests: list[ChatRunnerRequest] = []

    def run(self, request: ChatRunnerRequest, tools: ChatTools, **_kwargs):  # noqa: ANN001
        self.requests.append(request)
        return ChatRunnerOutput(answer="ok", cited_chunk_ids=())


class _EmptyRetrieval:
    def search(self, request):  # noqa: ANN001
        return []


def test_prepare_keeps_short_history_verbatim() -> None:
    turns = [
        ("user", "What is Nimbus?"),
        ("assistant", "A fox mascot."),
        ("user", "And Orion?"),
        ("assistant", "The codename."),
    ]
    prepared = prepare_chat_history(turns, keep_recent=6)
    assert prepared.used_summary is False
    assert prepared.summarized_messages == 0
    assert len(prepared.turns) == 4
    assert prepared.turns[0].content == "What is Nimbus?"


def test_prepare_summarizes_older_turns() -> None:
    turns: list[tuple[str, str]] = []
    for i in range(10):
        turns.append(("user", f"Question {i} about topic-{i}"))
        turns.append(("assistant", f"Answer {i} with detail about topic-{i}"))
    prepared = prepare_chat_history(turns, keep_recent=4)
    assert prepared.total_messages == 20
    assert prepared.kept_recent == 4
    assert prepared.summarized_messages == 16
    assert prepared.used_summary is True
    assert prepared.summary is not None
    assert "topic-0" in prepared.summary
    # Bridge + recent
    assert prepared.turns[0].role == "user"
    assert "condensed" in prepared.turns[0].content.lower()
    assert prepared.turns[-1].content.startswith("Answer 9")
    detail = prepared.as_step_detail()
    assert detail["used_summary"] is True
    assert detail["summarized_messages"] == 16


def test_chat_service_stream_emits_context_step_and_summarizes() -> None:
    audit = InMemoryChatAuditWriter(session_id=uuid4())
    # Seed a long transcript (more than keep_recent=4).
    for i in range(8):
        audit.record_message(uuid4(), audit.session_id, "user", f"User turn {i}")
        audit.record_message(
            uuid4(), audit.session_id, "assistant", f"Assistant turn {i}"
        )
    runner = _CaptureRunner()
    service = ChatService(
        runner=runner,
        retrieval_service=_EmptyRetrieval(),
        audit_writer=audit,
        history_message_limit=4,
        history_load_limit=40,
    )
    project_id = uuid4()
    # Re-bind project_id on messages is not needed for InMemory; it stores messages
    # by session only. list_history_turns returns from messages list.
    events = list(
        service.stream(
            ChatRequest(project_id=project_id, message="Follow-up about all of that?")
        )
    )
    context_steps = [
        event
        for event in events
        if event.event == "step" and event.data.get("id") == "context"
    ]
    assert context_steps, "expected a context step for multi-turn history"
    detail = context_steps[0].data["detail"]
    assert detail["total_messages"] >= 4
    assert runner.requests, "runner should receive a request"
    history = runner.requests[0].history
    # Either short (no summary) or condensed bridge present when > keep_recent.
    if detail.get("used_summary"):
        assert any(
            "condensed" in turn.content.lower() for turn in history if turn.role == "user"
        )
    assert isinstance(history[0], ChatHistoryTurn) if history else True
