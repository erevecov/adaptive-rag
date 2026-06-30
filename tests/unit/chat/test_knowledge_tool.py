from __future__ import annotations

from uuid import uuid4

from adaptive_rag.chat.tools import (
    ChatKnowledgeProposalTool,
    KnowledgeProposalSubmissionResult,
)


class RecordingSubmitter:
    def __init__(self) -> None:
        self.commits: list[tuple[str, str, str | None]] = []

    def commit(
        self,
        *,
        knowledge_text,
        scope,
        draft_id=None,
        **_kwargs,
    ):
        self.commits.append((knowledge_text, scope, draft_id))
        return KnowledgeProposalSubmissionResult(
            draft_id=draft_id or "draft-created",
            proposed_text=knowledge_text,
            review_action="approve",
            scope=scope,
            status="draft",
        )


def test_chat_knowledge_tool_records_refine_cancel_and_approve_lifecycle() -> None:
    submitter = RecordingSubmitter()
    tool = ChatKnowledgeProposalTool(
        submitter=submitter,
        project_id=uuid4(),
        submitted_by_user_id=uuid4(),
        origin_session_id=uuid4(),
        origin_message_id=uuid4(),
    )

    refined = tool.refine(
        draft_id="draft-123",
        knowledge_text="Refined project knowledge.",
        scope="session",
    )
    cancelled = tool.cancel(draft_id="draft-123")
    approved = tool.approve(draft_id="draft-123")

    assert refined == {
        "draft_id": "draft-123",
        "knowledge_lifecycle": {
            "action": "refine",
            "draft_id": "draft-123",
        },
        "proposed_text": "Refined project knowledge.",
        "review_action": "approve",
        "scope": "session",
        "status": "draft",
    }
    assert cancelled == {
        "draft_id": "draft-123",
        "knowledge_lifecycle": {
            "action": "cancel",
            "draft_id": "draft-123",
        },
        "status": "cancelled",
    }
    assert approved == {
        "draft_id": "draft-123",
        "knowledge_lifecycle": {
            "action": "approve",
            "draft_id": "draft-123",
        },
        "status": "approval_requested",
    }
    assert [call.name for call in tool.tool_calls] == [
        "refine_knowledge",
        "cancel_knowledge",
        "approve_knowledge",
    ]
    assert submitter.commits == [
        ("Refined project knowledge.", "session", "draft-123")
    ]
