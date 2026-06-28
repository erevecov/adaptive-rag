"""Routes for chat-sourced project knowledge proposal workflows."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from adaptive_rag import ingestion_ops
from adaptive_rag.api.dependencies import (
    get_current_user,
    get_project_access,
    get_project_contributor_access,
    get_session,
)
from adaptive_rag.api.schemas.knowledge import (
    KnowledgeProposalApproveRequestBody,
    KnowledgeProposalListResponse,
    KnowledgeProposalRefineRequestBody,
    KnowledgeProposalRejectRequestBody,
    KnowledgeProposalResponse,
    KnowledgeProposalSubmitRequestBody,
)
from adaptive_rag.auth import CurrentPrincipal, role_meets
from adaptive_rag.db.models import Project
from adaptive_rag.db.repositories import KnowledgeProposalRepository, SourceRepository

router = APIRouter(
    prefix="/projects/{project_id}/knowledge-proposals",
    tags=["knowledge-proposals"],
)


@router.post("", response_model=KnowledgeProposalResponse)
def submit_knowledge_proposal(
    project_id: UUID,
    body: KnowledgeProposalSubmitRequestBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    access: Annotated[tuple[Project, str], Depends(get_project_access)],
) -> KnowledgeProposalResponse:
    _project, role = access
    submitter_id = _require_authenticated_user_id(current)
    repo = KnowledgeProposalRepository(session)
    try:
        proposal = repo.create(
            project_id=project_id,
            submitted_by_user_id=submitter_id,
            proposed_text=body.proposed_text,
            origin_session_id=body.origin_session_id,
            origin_message_id=body.origin_message_id,
        )
        if role_meets(role, "contributor"):
            source_id = _create_approved_source(
                session=session,
                project_id=project_id,
                proposal_id=proposal.id,
                content=proposal.proposed_text,
            )
            proposal = repo.approve(
                project_id=project_id,
                proposal_id=proposal.id,
                reviewed_by_user_id=submitter_id,
                approved_source_id=source_id,
            )
    except ValueError as exc:
        raise _proposal_http_error(exc) from exc
    session.commit()
    return KnowledgeProposalResponse.from_proposal(proposal)


@router.get("", response_model=KnowledgeProposalListResponse)
def list_knowledge_proposals(
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Project, str], Depends(get_project_contributor_access)],
    status: Annotated[str | None, Query()] = None,
) -> KnowledgeProposalListResponse:
    try:
        proposals = KnowledgeProposalRepository(session).list_by_project(
            project_id=project_id,
            status=status,
        )
    except ValueError as exc:
        raise _proposal_http_error(exc) from exc
    return KnowledgeProposalListResponse.from_proposals(proposals)


@router.post("/{proposal_id}/refine", response_model=KnowledgeProposalResponse)
def refine_knowledge_proposal(
    project_id: UUID,
    proposal_id: UUID,
    body: KnowledgeProposalRefineRequestBody,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Project, str], Depends(get_project_contributor_access)],
) -> KnowledgeProposalResponse:
    try:
        proposal = KnowledgeProposalRepository(session).refine(
            project_id=project_id,
            proposal_id=proposal_id,
            refined_text=body.refined_text,
        )
    except ValueError as exc:
        raise _proposal_http_error(exc) from exc
    session.commit()
    return KnowledgeProposalResponse.from_proposal(proposal)


@router.post("/{proposal_id}/approve", response_model=KnowledgeProposalResponse)
def approve_knowledge_proposal(
    project_id: UUID,
    proposal_id: UUID,
    body: KnowledgeProposalApproveRequestBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[Project, str], Depends(get_project_contributor_access)],
) -> KnowledgeProposalResponse:
    reviewer_id = _require_authenticated_user_id(current)
    repo = KnowledgeProposalRepository(session)
    try:
        if body.refined_text is not None:
            proposal = repo.refine(
                project_id=project_id,
                proposal_id=proposal_id,
                refined_text=body.refined_text,
            )
        else:
            existing = repo.get(project_id=project_id, proposal_id=proposal_id)
            if existing is None:
                raise ValueError("knowledge_proposal_not_found")
            if existing.status != "pending":
                raise ValueError("knowledge_proposal_not_pending")
            proposal = existing
        content = proposal.refined_text or proposal.proposed_text
        source_id = _create_approved_source(
            session=session,
            project_id=project_id,
            proposal_id=proposal_id,
            content=content,
        )
        proposal = repo.approve(
            project_id=project_id,
            proposal_id=proposal_id,
            reviewed_by_user_id=reviewer_id,
            approved_source_id=source_id,
            review_note=body.review_note,
        )
    except ValueError as exc:
        raise _proposal_http_error(exc) from exc
    session.commit()
    return KnowledgeProposalResponse.from_proposal(proposal)


@router.post("/{proposal_id}/reject", response_model=KnowledgeProposalResponse)
def reject_knowledge_proposal(
    project_id: UUID,
    proposal_id: UUID,
    body: KnowledgeProposalRejectRequestBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[Project, str], Depends(get_project_contributor_access)],
) -> KnowledgeProposalResponse:
    reviewer_id = _require_authenticated_user_id(current)
    try:
        proposal = KnowledgeProposalRepository(session).reject(
            project_id=project_id,
            proposal_id=proposal_id,
            reviewed_by_user_id=reviewer_id,
            reason=body.reason,
        )
    except ValueError as exc:
        raise _proposal_http_error(exc) from exc
    session.commit()
    return KnowledgeProposalResponse.from_proposal(proposal)


def _create_approved_source(
    *,
    session: Session,
    project_id: UUID,
    proposal_id: UUID,
    content: str,
) -> UUID:
    source = SourceRepository(session).create(
        project_id=project_id,
        source_type="markdown",
        external_id=f"chat-proposal:{proposal_id}",
        tags=["chat-proposal"],
        extra_metadata={"content": content},
    )
    ingestion_ops.enqueue_source_ingestion(
        session,
        project_id=project_id,
        source_id=source.id,
    )
    return source.id


def _require_authenticated_user_id(current: CurrentPrincipal) -> UUID:
    if current.user_id is None:
        raise HTTPException(status_code=401, detail="authenticated user required")
    return current.user_id


def _proposal_http_error(error: ValueError) -> HTTPException:
    detail = str(error)
    status_code = 404 if detail == "knowledge_proposal_not_found" else 422
    return HTTPException(status_code=status_code, detail=detail)
