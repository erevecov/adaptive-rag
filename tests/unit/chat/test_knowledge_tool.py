from __future__ import annotations

from uuid import uuid4

from adaptive_rag.chat.tools import (
    ChatKnowledgeProposalTool,
    KnowledgeProposalSubmissionResult,
)


class RecordingSubmitter:
    def __init__(self) -> None:
        self.commits: list[tuple[str, str, str | None]] = []
        self.refines: list[tuple[str, str, str]] = []
        self.cancels: list[str] = []

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
            status="pending",
        )

    def refine(
        self,
        *,
        project_id,  # noqa: ANN001
        draft_id,
        knowledge_text,
        scope,
    ):
        self.refines.append((draft_id, knowledge_text, scope))
        return KnowledgeProposalSubmissionResult(
            draft_id=draft_id,
            proposed_text=knowledge_text,
            review_action="approve",
            scope=scope,
            status="pending",
        )

    def cancel(
        self,
        *,
        project_id,  # noqa: ANN001
        draft_id,
        reviewed_by_user_id,  # noqa: ANN001
        scope="message",
    ):
        self.cancels.append(draft_id)
        return KnowledgeProposalSubmissionResult(
            draft_id=draft_id,
            proposed_text="stale",
            review_action="none",
            scope=scope,
            status="rejected",
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
        "status": "pending",
    }
    assert cancelled == {
        "draft_id": "draft-123",
        "knowledge_lifecycle": {
            "action": "cancel",
            "draft_id": "draft-123",
        },
        "proposed_text": "stale",
        "review_action": "none",
        "scope": "message",
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
    assert submitter.refines == [
        ("draft-123", "Refined project knowledge.", "session")
    ]
    assert submitter.cancels == ["draft-123"]
    assert submitter.commits == []
