"""Vision routing + attachment injection for ChatService."""

from __future__ import annotations

from uuid import uuid4

import pytest

from adaptive_rag.chat.attachments import ChatAttachmentContext
from adaptive_rag.chat.errors import ChatServiceError
from adaptive_rag.chat.models import ChatRequest, ChatRunnerOutput, ChatRunnerRequest
from adaptive_rag.chat.service import ChatService
from adaptive_rag.chat.tools import ChatTools


class _CapsRunner:
    def __init__(self, caps: tuple[str, ...] | None, label: str = "chat") -> None:
        self.model_capabilities = caps
        self.label = label
        self.calls = 0

    def run(self, request: ChatRunnerRequest, tools: ChatTools) -> ChatRunnerOutput:
        self.calls += 1
        n = sum(1 for a in request.attachments if a.kind == "image")
        return ChatRunnerOutput(answer=f"{self.label}:{n}", cited_chunk_ids=())


class _Retrieval:
    def search(self, **kwargs):  # noqa: ANN003
        raise AssertionError("should not retrieve in these unit tests")


def _image_ctx() -> ChatAttachmentContext:
    return ChatAttachmentContext(
        id=uuid4(),
        kind="image",
        filename="x.png",
        mime="image/png",
        image_data_url="data:image/png;base64,abc",
    )


def test_uses_chat_runner_when_vision_capable() -> None:
    chat = _CapsRunner(("chat", "vision"), "chat")
    vision = _CapsRunner(("chat", "vision"), "vision")
    service = ChatService(
        runner=chat,  # type: ignore[arg-type]
        retrieval_service=_Retrieval(),  # type: ignore[arg-type]
        attachment_loader=lambda **_: (_image_ctx(),),
        vision_runner_factory=lambda _ws: vision,  # type: ignore[arg-type,return-value]
    )
    # respond needs audit - use without session by mocking audit that returns None
    from adaptive_rag.chat.audit import NullChatAuditWriter

    service._audit_writer = NullChatAuditWriter()  # noqa: SLF001
    response = service.respond(
        ChatRequest(workspace_id=uuid4(), message="see image", attachments=(uuid4(),))
    )
    assert response.answer.startswith("chat:")
    assert chat.calls == 1
    assert vision.calls == 0


def test_falls_back_to_vision_slot() -> None:
    chat = _CapsRunner(("chat",), "chat")
    vision = _CapsRunner(("chat", "vision"), "vision")
    service = ChatService(
        runner=chat,  # type: ignore[arg-type]
        retrieval_service=_Retrieval(),  # type: ignore[arg-type]
        attachment_loader=lambda **_: (_image_ctx(),),
        vision_runner_factory=lambda _ws: vision,  # type: ignore[arg-type,return-value]
    )
    from adaptive_rag.chat.audit import NullChatAuditWriter

    service._audit_writer = NullChatAuditWriter()  # noqa: SLF001
    response = service.respond(
        ChatRequest(workspace_id=uuid4(), message="see image", attachments=(uuid4(),))
    )
    assert response.answer.startswith("vision:")
    assert vision.calls == 1
    assert chat.calls == 0


def test_422_when_no_vision_path() -> None:
    chat = _CapsRunner(("chat",), "chat")
    service = ChatService(
        runner=chat,  # type: ignore[arg-type]
        retrieval_service=_Retrieval(),  # type: ignore[arg-type]
        attachment_loader=lambda **_: (_image_ctx(),),
        vision_runner_factory=lambda _ws: None,
    )
    from adaptive_rag.chat.audit import NullChatAuditWriter

    service._audit_writer = NullChatAuditWriter()  # noqa: SLF001
    with pytest.raises(ChatServiceError) as exc_info:
        service.respond(
            ChatRequest(
                workspace_id=uuid4(), message="see image", attachments=(uuid4(),)
            )
        )
    assert exc_info.value.code == "vision_model_required"
