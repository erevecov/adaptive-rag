"""Persistence adapter for chat-driven knowledge proposal tools."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.auth import role_meets
from adaptive_rag.chat.tools import KnowledgeProposalSubmissionResult
from adaptive_rag.db.repositories import KnowledgeProposalRepository


class SqlAlchemyKnowledgeProposalSubmitter:
    """Create and lifecycle durable chat-sourced knowledge proposals."""

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
                    return self._to_result(existing, scope=scope)

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
                    return self._to_result(proposal, scope=scope)

        proposal = repo.create(
            project_id=project_id,
            submitted_by_user_id=submitted_by_user_id,
            proposed_text=text,
            origin_session_id=origin_session_id,
            origin_message_id=origin_message_id,
        )
        return self._to_result(proposal, scope=scope)

    def refine(
        self,
        *,
        project_id: UUID,
        draft_id: str,
        knowledge_text: str,
        scope: str,
    ) -> KnowledgeProposalSubmissionResult:
        repo = KnowledgeProposalRepository(self._session)
        proposal_id = _parse_uuid(draft_id, label="draft_id")
        proposal = repo.refine(
            project_id=project_id,
            proposal_id=proposal_id,
            refined_text=knowledge_text.strip(),
        )
        return self._to_result(proposal, scope=scope)

    def cancel(
        self,
        *,
        project_id: UUID,
        draft_id: str,
        reviewed_by_user_id: UUID,
        scope: str = "message",
    ) -> KnowledgeProposalSubmissionResult:
        repo = KnowledgeProposalRepository(self._session)
        proposal_id = _parse_uuid(draft_id, label="draft_id")
        proposal = repo.reject(
            project_id=project_id,
            proposal_id=proposal_id,
            reviewed_by_user_id=reviewed_by_user_id,
            reason="Canceled from chat",
        )
        return KnowledgeProposalSubmissionResult(
            draft_id=str(proposal.id),
            proposed_text=proposal.refined_text or proposal.proposed_text,
            review_action="none",
            scope=scope,
            status="rejected",
        )

    def _to_result(
        self,
        proposal: object,
        *,
        scope: str,
    ) -> KnowledgeProposalSubmissionResult:
        proposed_text = getattr(proposal, "refined_text", None) or getattr(
            proposal, "proposed_text"
        )
        return KnowledgeProposalSubmissionResult(
            draft_id=str(getattr(proposal, "id")),
            proposed_text=str(proposed_text),
            review_action=(
                "approve"
                if role_meets(self._project_role, "contributor")
                else "request_approval"
            ),
            scope=scope,
            status=str(getattr(proposal, "status")),
        )


def _parse_uuid(value: str, *, label: str) -> UUID:
    try:
        return UUID(value.strip())
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid UUID") from exc
