"""Schemas HTTP for chat-sourced knowledge proposals."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from adaptive_rag.db.models import KnowledgeProposal


class KnowledgeProposalSubmitRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposed_text: str
    origin_session_id: UUID | None = None
    origin_message_id: UUID | None = None


class KnowledgeProposalRefineRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refined_text: str


class KnowledgeProposalApproveRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refined_text: str | None = None
    review_note: str | None = None


class KnowledgeProposalRejectRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str


class KnowledgeProposalResponse(BaseModel):
    id: UUID
    project_id: UUID
    submitted_by_user_id: UUID | None
    origin_session_id: UUID | None
    origin_message_id: UUID | None
    approved_source_id: UUID | None
    reviewed_by_user_id: UUID | None
    status: str
    proposed_text: str
    refined_text: str | None
    review_note: str | None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None

    @classmethod
    def from_proposal(
        cls,
        proposal: KnowledgeProposal,
    ) -> KnowledgeProposalResponse:
        return cls(
            id=proposal.id,
            project_id=proposal.project_id,
            submitted_by_user_id=proposal.submitted_by_user_id,
            origin_session_id=proposal.origin_session_id,
            origin_message_id=proposal.origin_message_id,
            approved_source_id=proposal.approved_source_id,
            reviewed_by_user_id=proposal.reviewed_by_user_id,
            status=proposal.status,
            proposed_text=proposal.proposed_text,
            refined_text=proposal.refined_text,
            review_note=proposal.review_note,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
            reviewed_at=proposal.reviewed_at,
        )


class KnowledgeProposalListResponse(BaseModel):
    items: list[KnowledgeProposalResponse]

    @classmethod
    def from_proposals(
        cls,
        proposals: list[KnowledgeProposal],
    ) -> KnowledgeProposalListResponse:
        return cls(
            items=[
                KnowledgeProposalResponse.from_proposal(proposal)
                for proposal in proposals
            ]
        )
