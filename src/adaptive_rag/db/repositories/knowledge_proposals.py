"""Repository for chat-sourced knowledge proposal review workflows."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import (
    KNOWLEDGE_PROPOSAL_STATUS_VALUES,
    KnowledgeProposal,
    Source,
    User,
)
from adaptive_rag.db.models.chat_message import ChatMessage
from adaptive_rag.db.models.chat_session import ChatSession
from adaptive_rag.db.models.job import utc_now


class KnowledgeProposalRepository:
    """Persistence for project-scoped chat knowledge proposals.

    Transactions are controlled by the caller. Methods flush but do not commit.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        project_id: UUID,
        submitted_by_user_id: UUID,
        proposed_text: str,
        origin_session_id: UUID | None = None,
        origin_message_id: UUID | None = None,
    ) -> KnowledgeProposal:
        self._require_user(submitted_by_user_id)
        if origin_session_id is not None:
            self._require_session(project_id=project_id, session_id=origin_session_id)
        if origin_message_id is not None:
            self._require_message(project_id=project_id, message_id=origin_message_id)

        proposal = KnowledgeProposal(
            project_id=project_id,
            submitted_by_user_id=submitted_by_user_id,
            origin_session_id=origin_session_id,
            origin_message_id=origin_message_id,
            proposed_text=_normalize_non_empty(proposed_text, "proposed_text"),
        )
        self._session.add(proposal)
        self._session.flush()
        return proposal

    def get(
        self,
        *,
        project_id: UUID,
        proposal_id: UUID,
    ) -> KnowledgeProposal | None:
        statement = select(KnowledgeProposal).where(
            KnowledgeProposal.project_id == project_id,
            KnowledgeProposal.id == proposal_id,
        )
        return self._session.scalars(statement).one_or_none()

    def list_by_project(
        self,
        *,
        project_id: UUID,
        status: str | None = None,
    ) -> list[KnowledgeProposal]:
        statement = select(KnowledgeProposal).where(
            KnowledgeProposal.project_id == project_id
        )
        if status is not None:
            statement = statement.where(
                KnowledgeProposal.status
                == _normalize_supported_status(status)
            )
        statement = statement.order_by(
            KnowledgeProposal.created_at,
            KnowledgeProposal.id,
        )
        return list(self._session.scalars(statement))

    def list_by_submitter(
        self,
        *,
        project_id: UUID,
        submitted_by_user_id: UUID,
    ) -> list[KnowledgeProposal]:
        statement = (
            select(KnowledgeProposal)
            .where(
                KnowledgeProposal.project_id == project_id,
                KnowledgeProposal.submitted_by_user_id == submitted_by_user_id,
            )
            .order_by(KnowledgeProposal.created_at, KnowledgeProposal.id)
        )
        return list(self._session.scalars(statement))

    def refine(
        self,
        *,
        project_id: UUID,
        proposal_id: UUID,
        refined_text: str,
    ) -> KnowledgeProposal:
        proposal = self._require_pending(project_id=project_id, proposal_id=proposal_id)
        proposal.refined_text = _normalize_non_empty(refined_text, "refined_text")
        self._session.flush()
        return proposal

    def approve(
        self,
        *,
        project_id: UUID,
        proposal_id: UUID,
        reviewed_by_user_id: UUID,
        approved_source_id: UUID,
        review_note: str | None = None,
    ) -> KnowledgeProposal:
        proposal = self._require_pending(project_id=project_id, proposal_id=proposal_id)
        self._require_user(reviewed_by_user_id)
        self._require_source(project_id=project_id, source_id=approved_source_id)

        proposal.status = "approved"
        proposal.reviewed_by_user_id = reviewed_by_user_id
        proposal.approved_source_id = approved_source_id
        proposal.review_note = review_note.strip() if review_note is not None else None
        proposal.reviewed_at = utc_now()
        self._session.flush()
        return proposal

    def reject(
        self,
        *,
        project_id: UUID,
        proposal_id: UUID,
        reviewed_by_user_id: UUID,
        reason: str,
    ) -> KnowledgeProposal:
        proposal = self._require_pending(project_id=project_id, proposal_id=proposal_id)
        self._require_user(reviewed_by_user_id)
        review_note = _normalize_non_empty(reason, "rejection_reason")

        proposal.status = "rejected"
        proposal.reviewed_by_user_id = reviewed_by_user_id
        proposal.review_note = review_note
        proposal.reviewed_at = utc_now()
        self._session.flush()
        return proposal

    def _require_pending(
        self,
        *,
        project_id: UUID,
        proposal_id: UUID,
    ) -> KnowledgeProposal:
        proposal = self.get(project_id=project_id, proposal_id=proposal_id)
        if proposal is None:
            raise ValueError("knowledge_proposal_not_found")
        if proposal.status != "pending":
            raise ValueError("knowledge_proposal_not_pending")
        return proposal

    def _require_user(self, user_id: UUID) -> User:
        user = self._session.get(User, user_id)
        if user is None:
            raise ValueError("user_not_found")
        return user

    def _require_source(self, *, project_id: UUID, source_id: UUID) -> Source:
        statement = select(Source).where(
            Source.project_id == project_id,
            Source.id == source_id,
        )
        source = self._session.scalars(statement).one_or_none()
        if source is None:
            raise ValueError("source does not belong to project")
        return source

    def _require_session(self, *, project_id: UUID, session_id: UUID) -> ChatSession:
        statement = select(ChatSession).where(
            ChatSession.project_id == project_id,
            ChatSession.id == session_id,
        )
        chat_session = self._session.scalars(statement).one_or_none()
        if chat_session is None:
            raise ValueError("chat session does not belong to project")
        return chat_session

    def _require_message(self, *, project_id: UUID, message_id: UUID) -> ChatMessage:
        statement = select(ChatMessage).where(
            ChatMessage.project_id == project_id,
            ChatMessage.id == message_id,
        )
        message = self._session.scalars(statement).one_or_none()
        if message is None:
            raise ValueError("chat message does not belong to project")
        return message


def _normalize_non_empty(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        if label == "rejection_reason":
            raise ValueError("rejection_reason_required")
        raise ValueError(f"{label} must not be empty")
    return normalized


def _normalize_supported_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in KNOWLEDGE_PROPOSAL_STATUS_VALUES:
        raise ValueError(f"unsupported knowledge proposal status: {normalized}")
    return normalized
