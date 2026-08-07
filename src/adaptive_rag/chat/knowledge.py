"""Persistence adapter for chat-driven knowledge proposal tools."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.auth import role_meets
from adaptive_rag.chat.tools import KnowledgeProposalSubmissionResult
from adaptive_rag.db.repositories import KnowledgeProposalRepository


class SqlAlchemyKnowledgeProposalSubmitter:
    """Create durable chat-sourced knowledge proposals (pending review)."""

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
        repo = KnowledgeProposalRepository(self._session)
        text = knowledge_text.strip()
        # Idempotent re-commit of an existing pending proposal id.
        if draft_id is not None:
            try:
                existing_id = UUID(draft_id)
            except ValueError:
                existing_id = None
            if existing_id is not None:
                existing = repo.get(project_id=project_id, proposal_id=existing_id)
                if existing is not None and existing.status == "pending":
                    return KnowledgeProposalSubmissionResult(
                        draft_id=str(existing.id),
                        proposed_text=existing.refined_text or existing.proposed_text,
                        review_action=(
                            "approve"
                            if role_meets(self._project_role, "contributor")
                            else "request_approval"
                        ),
                        scope=scope,
                        status="pending",
                    )

        # Soft idempotency: same session + same text → reuse pending row.
        if origin_session_id is not None:
            for proposal in repo.list_by_project(
                project_id=project_id, status="pending"
            ):
                if (
                    proposal.origin_session_id == origin_session_id
                    and (proposal.refined_text or proposal.proposed_text).strip()
                    == text
                ):
                    return KnowledgeProposalSubmissionResult(
                        draft_id=str(proposal.id),
                        proposed_text=proposal.refined_text or proposal.proposed_text,
                        review_action=(
                            "approve"
                            if role_meets(self._project_role, "contributor")
                            else "request_approval"
                        ),
                        scope=scope,
                        status="pending",
                    )

        proposal = repo.create(
            project_id=project_id,
            submitted_by_user_id=submitted_by_user_id,
            proposed_text=text,
            origin_session_id=origin_session_id,
            origin_message_id=origin_message_id,
        )
        return KnowledgeProposalSubmissionResult(
            draft_id=str(proposal.id),
            proposed_text=proposal.proposed_text,
            review_action=(
                "approve"
                if role_meets(self._project_role, "contributor")
                else "request_approval"
            ),
            scope=scope,
            status="pending",
        )
