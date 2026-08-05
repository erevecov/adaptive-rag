"""Bloque C: durable user memory propose/approve/inject."""

from __future__ import annotations

from adaptive_rag import user_memory
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Project, User, UserMemory
from adaptive_rag.db.repositories import ProjectRepository, UserRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Project.__table__, User.__table__, UserMemory.__table__],
    )
    return create_session_factory(engine)()


def test_propose_approve_and_injection_text() -> None:
    session = _session()
    project = ProjectRepository(session).create(name="MemProj")
    user = UserRepository(session).create_user(
        login="mem-user",
        display_name="Mem User",
        system_role="user",
    )
    session.commit()

    proposed = user_memory.propose_memory(
        session,
        user_id=user.id,
        project_id=project.id,
        content="  Prefers Spanish answers  ",
    )
    assert proposed.status == "proposed"
    assert proposed.content == "Prefers Spanish answers"

    # Not injected until approved
    assert (
        user_memory.approved_injection_text(
            session, user_id=user.id, project_id=project.id
        )
        == ""
    )

    approved = user_memory.approve_memory(
        session,
        memory_id=proposed.id,
        reviewer_user_id=user.id,
        owner_user_id=user.id,
    )
    assert approved.status == "approved"
    injection = user_memory.approved_injection_text(
        session, user_id=user.id, project_id=project.id
    )
    assert "User memory (approved):" in injection
    assert "Prefers Spanish answers" in injection


def test_reject_blocks_injection_and_double_review() -> None:
    session = _session()
    user = UserRepository(session).create_user(
        login="mem-user-2",
        display_name="Mem 2",
        system_role="user",
    )
    memory = user_memory.propose_memory(
        session, user_id=user.id, content="Remember my timezone is UTC"
    )
    rejected = user_memory.reject_memory(
        session,
        memory_id=memory.id,
        reviewer_user_id=user.id,
        owner_user_id=user.id,
    )
    assert rejected.status == "rejected"
    assert user_memory.approved_injection_text(session, user_id=user.id) == ""

    try:
        user_memory.approve_memory(
            session,
            memory_id=memory.id,
            reviewer_user_id=user.id,
            owner_user_id=user.id,
        )
        raise AssertionError("expected conflict")
    except user_memory.UserMemoryError as exc:
        assert exc.status_code == 409


def test_empty_content_rejected() -> None:
    session = _session()
    user = UserRepository(session).create_user(
        login="mem-user-3",
        display_name="Mem 3",
        system_role="user",
    )
    try:
        user_memory.propose_memory(session, user_id=user.id, content="   ")
        raise AssertionError("expected empty error")
    except user_memory.UserMemoryError as exc:
        assert exc.status_code == 422


def test_cross_user_cannot_approve_foreign_memory() -> None:
    session = _session()
    users = UserRepository(session)
    owner = users.create_user(login="owner", display_name="Owner")
    other = users.create_user(login="other", display_name="Other")
    memory = user_memory.propose_memory(
        session, user_id=owner.id, content="Secret preference"
    )
    try:
        user_memory.approve_memory(
            session,
            memory_id=memory.id,
            reviewer_user_id=other.id,
            owner_user_id=other.id,
        )
        raise AssertionError("expected not found for foreign owner scope")
    except user_memory.UserMemoryError as exc:
        assert exc.status_code == 404

    assert memory.status == "proposed"
    assert user_memory.approved_injection_text(session, user_id=owner.id) == ""
    assert user_memory.approved_injection_text(session, user_id=other.id) == ""


def test_global_and_project_scope_injection() -> None:
    session = _session()
    project = ProjectRepository(session).create(name="Scoped")
    user = UserRepository(session).create_user(login="scoped", display_name="Scoped")
    global_mem = user_memory.propose_memory(
        session, user_id=user.id, content="Global preference"
    )
    project_mem = user_memory.propose_memory(
        session,
        user_id=user.id,
        project_id=project.id,
        content="Project preference",
    )
    for mem in (global_mem, project_mem):
        user_memory.approve_memory(
            session,
            memory_id=mem.id,
            reviewer_user_id=user.id,
            owner_user_id=user.id,
        )

    text = user_memory.approved_injection_text(
        session, user_id=user.id, project_id=project.id
    )
    assert "Global preference" in text
    assert "Project preference" in text

    global_only = user_memory.approved_injection_text(session, user_id=user.id)
    assert "Global preference" in global_only
    # Without project filter, project-scoped rows are still listed
    # when project_id is None (list_for_user only filters by project
    # when project_id is provided).
