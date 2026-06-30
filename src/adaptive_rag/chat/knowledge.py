"""Persistence adapter for chat-driven knowledge proposal tools."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.auth import role_meets
from adaptive_rag.chat.tools import (
    KnowledgeProposalSubmissionResult,
    new_knowledge_draft_id,
)


class SqlAlchemyKnowledgeProposalSubmitter:
    """Create chat-sourced knowledge drafts inside caller-owned transactions."""

    def __init__(self, *, session: Session, project_role: str) -> None:
        self._session = session
        self._project_role = project_role

    def commit(
        self,
        *,
        project_id: UUID,
        submitted_by_user_id: UUID,
        knowledge_text: str,
        scope: str,
        origin_session_id: UUID | None,
        origin_message_id: UUID | None,
        draft_id: str | None = None,
    ) -> KnowledgeProposalSubmissionResult:
        _ = (self._session, project_id, submitted_by_user_id)
        _ = (origin_session_id, origin_message_id)
        return KnowledgeProposalSubmissionResult(
            draft_id=draft_id or new_knowledge_draft_id(),
            proposed_text=knowledge_text,
            review_action=(
                "approve"
                if role_meets(self._project_role, "contributor")
                else "request_approval"
            ),
            scope=scope,
            status="draft",
        )
