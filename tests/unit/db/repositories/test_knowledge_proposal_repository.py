"""Tests para repository de propuestas de conocimiento desde chat."""

from __future__ import annotations

import pytest

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    ChatMessage,
    ChatSession,
    KnowledgeProposal,
    Source,
    User,
    Workspace,
)
from adaptive_rag.db.repositories import (
    KnowledgeProposalRepository,
    SourceRepository,
    UserRepository,
    WorkspaceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Workspace.__table__,
            User.__table__,
            Source.__table__,
            ChatSession.__table__,
            ChatMessage.__table__,
            KnowledgeProposal.__table__,
        ],
    )
    return create_session_factory(engine)()


def _make_user(session, email: str = "viewer@example.com") -> User:
    return UserRepository(session).create_user(email=email, display_name=email)


def _make_origin(session, *, workspace: Workspace, user: User) -> ChatMessage:
    chat_session = ChatSession(workspace_id=workspace.id, user_id=user.id)
    session.add(chat_session)
    session.flush()
    message = ChatMessage(
        workspace_id=workspace.id,
        session_id=chat_session.id,
        role="user",
        content="Please add this",
    )
    session.add(message)
    session.flush()
    return message


def _make_source(
    session, *, workspace: Workspace, external_id: str = "approved"
) -> Source:
    return SourceRepository(session).create(
        workspace_id=workspace.id,
        source_type="chat_proposal",
        external_id=external_id,
    )


def test_repository_creates_pending_proposal_without_committing() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    user = _make_user(session)
    message = _make_origin(session, workspace=workspace, user=user)
    proposal = KnowledgeProposalRepository(session).create(
        workspace_id=workspace.id,
        submitted_by_user_id=user.id,
        proposed_text="New knowledge",
        origin_session_id=message.session_id,
        origin_message_id=message.id,
    )
    proposal_id = proposal.id

    assert proposal.status == "pending"
    assert proposal.submitted_by_user_id == user.id
    assert proposal.origin_message_id == message.id

    session.rollback()
    session.expunge_all()

    assert (
        KnowledgeProposalRepository(session).get(
            workspace_id=workspace.id,
            proposal_id=proposal_id,
        )
        is None
    )


def test_repository_lists_workspace_and_submitter_proposals_in_order() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    other_workspace = WorkspaceRepository(session).create(name="other")
    user = _make_user(session, "viewer@example.com")
    other_user = _make_user(session, "other@example.com")
    repo = KnowledgeProposalRepository(session)
    first = repo.create(
        workspace_id=workspace.id,
        submitted_by_user_id=user.id,
        proposed_text="First",
    )
    second = repo.create(
        workspace_id=workspace.id,
        submitted_by_user_id=user.id,
        proposed_text="Second",
    )
    repo.create(
        workspace_id=workspace.id,
        submitted_by_user_id=other_user.id,
        proposed_text="Other user",
    )
    repo.create(
        workspace_id=other_workspace.id,
        submitted_by_user_id=user.id,
        proposed_text="Other workspace",
    )
    session.commit()

    assert [item.id for item in repo.list_by_workspace(workspace_id=workspace.id)] == [
        first.id,
        second.id,
        repo.list_by_submitter(
            workspace_id=workspace.id,
            submitted_by_user_id=other_user.id,
        )[0].id,
    ]
    assert [
        item.id
        for item in repo.list_by_submitter(
            workspace_id=workspace.id,
            submitted_by_user_id=user.id,
        )
    ] == [first.id, second.id]


def test_repository_refines_only_pending_workspace_proposal() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    other_workspace = WorkspaceRepository(session).create(name="other")
    user = _make_user(session)
    repo = KnowledgeProposalRepository(session)
    proposal = repo.create(
        workspace_id=workspace.id,
        submitted_by_user_id=user.id,
        proposed_text="Draft",
    )
    session.commit()

    refined = repo.refine(
        workspace_id=workspace.id,
        proposal_id=proposal.id,
        refined_text="Refined draft",
    )

    assert refined.refined_text == "Refined draft"
    with pytest.raises(ValueError, match="knowledge_proposal_not_found"):
        repo.refine(
            workspace_id=other_workspace.id,
            proposal_id=proposal.id,
            refined_text="Cross workspace",
        )


def test_repository_approves_pending_proposal_with_reviewer_and_source() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    user = _make_user(session)
    reviewer = _make_user(session, "reviewer@example.com")
    source = _make_source(session, workspace=workspace)
    repo = KnowledgeProposalRepository(session)
    proposal = repo.create(
        workspace_id=workspace.id,
        submitted_by_user_id=user.id,
        proposed_text="Draft",
    )
    session.commit()

    approved = repo.approve(
        workspace_id=workspace.id,
        proposal_id=proposal.id,
        reviewed_by_user_id=reviewer.id,
        approved_source_id=source.id,
        review_note="accepted",
    )

    assert approved.status == "approved"
    assert approved.reviewed_by_user_id == reviewer.id
    assert approved.approved_source_id == source.id
    assert approved.review_note == "accepted"
    assert approved.reviewed_at is not None
    with pytest.raises(ValueError, match="knowledge_proposal_not_pending"):
        repo.refine(
            workspace_id=workspace.id,
            proposal_id=proposal.id,
            refined_text="Too late",
        )


def test_repository_rejects_pending_proposal_with_required_reason() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    user = _make_user(session)
    reviewer = _make_user(session, "reviewer@example.com")
    repo = KnowledgeProposalRepository(session)
    proposal = repo.create(
        workspace_id=workspace.id,
        submitted_by_user_id=user.id,
        proposed_text="Draft",
    )
    session.commit()

    with pytest.raises(ValueError, match="rejection_reason_required"):
        repo.reject(
            workspace_id=workspace.id,
            proposal_id=proposal.id,
            reviewed_by_user_id=reviewer.id,
            reason=" ",
        )

    rejected = repo.reject(
        workspace_id=workspace.id,
        proposal_id=proposal.id,
        reviewed_by_user_id=reviewer.id,
        reason="not useful",
    )

    assert rejected.status == "rejected"
    assert rejected.review_note == "not useful"
    assert rejected.reviewed_by_user_id == reviewer.id
    with pytest.raises(ValueError, match="knowledge_proposal_not_pending"):
        repo.approve(
            workspace_id=workspace.id,
            proposal_id=proposal.id,
            reviewed_by_user_id=reviewer.id,
            approved_source_id=_make_source(session, workspace=workspace).id,
        )


def test_repository_rejects_approval_source_from_different_workspace() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    other_workspace = WorkspaceRepository(session).create(name="other")
    user = _make_user(session)
    reviewer = _make_user(session, "reviewer@example.com")
    other_source = _make_source(session, workspace=other_workspace)
    repo = KnowledgeProposalRepository(session)
    proposal = repo.create(
        workspace_id=workspace.id,
        submitted_by_user_id=user.id,
        proposed_text="Draft",
    )

    with pytest.raises(ValueError, match="source does not belong to workspace"):
        repo.approve(
            workspace_id=workspace.id,
            proposal_id=proposal.id,
            reviewed_by_user_id=reviewer.id,
            approved_source_id=other_source.id,
        )
