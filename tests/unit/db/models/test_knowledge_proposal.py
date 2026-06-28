"""Tests para modelo de propuestas de conocimiento desde chat."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    ChatMessage,
    ChatSession,
    KnowledgeProposal,
    Project,
    Source,
    User,
)
from adaptive_rag.db.repositories import ProjectRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            User.__table__,
            Source.__table__,
            ChatSession.__table__,
            ChatMessage.__table__,
            KnowledgeProposal.__table__,
        ],
    )
    return create_session_factory(engine)()


def test_knowledge_proposal_persists_chat_origin_and_defaults_to_pending() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    user = User(login="viewer@example.com", display_name="Viewer")
    reviewer = User(login="reviewer@example.com", display_name="Reviewer")
    session.add_all([user, reviewer])
    session.flush()
    chat_session = ChatSession(project_id=project.id, user_id=user.id)
    session.add(chat_session)
    session.flush()
    message = ChatMessage(
        project_id=project.id,
        session_id=chat_session.id,
        role="user",
        content="Add this as knowledge",
    )
    source = Source(
        project_id=project.id,
        source_type="chat_proposal",
        external_id="proposal-source",
    )
    session.add_all([message, source])
    session.flush()

    proposal = KnowledgeProposal(
        project_id=project.id,
        submitted_by_user_id=user.id,
        origin_session_id=chat_session.id,
        origin_message_id=message.id,
        proposed_text="Original knowledge",
        refined_text="Refined knowledge",
        reviewed_by_user_id=reviewer.id,
        approved_source_id=source.id,
        review_note="looks good",
    )
    session.add(proposal)
    session.commit()
    fetched = session.get(KnowledgeProposal, proposal.id)

    assert fetched is not None
    assert fetched.project_id == project.id
    assert fetched.submitted_by_user_id == user.id
    assert fetched.origin_session_id == chat_session.id
    assert fetched.origin_message_id == message.id
    assert fetched.proposed_text == "Original knowledge"
    assert fetched.refined_text == "Refined knowledge"
    assert fetched.status == "pending"
    assert fetched.reviewed_by_user_id == reviewer.id
    assert fetched.approved_source_id == source.id
    assert fetched.review_note == "looks good"


def test_knowledge_proposal_rejects_unsupported_status() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    user = User(login="viewer@example.com", display_name="Viewer")
    session.add(user)
    session.flush()
    session.add(
        KnowledgeProposal(
            project_id=project.id,
            submitted_by_user_id=user.id,
            proposed_text="Knowledge",
            status="needs-work",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_knowledge_proposal_has_project_status_indexes() -> None:
    indexes = {
        tuple(column.name for column in index.columns)
        for index in KnowledgeProposal.__table__.indexes
    }

    assert ("project_id", "status", "created_at") in indexes
    assert ("project_id", "submitted_by_user_id", "created_at") in indexes
    assert ("project_id", "origin_session_id") in indexes
