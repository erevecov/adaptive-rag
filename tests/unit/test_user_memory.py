"""Bloque C: durable user memory propose/approve/inject."""

from __future__ import annotations

from adaptive_rag import user_memory
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import User, UserMemory, Workspace, WorkspaceMembership
from adaptive_rag.db.repositories import (
    UserRepository,
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Workspace.__table__,
            User.__table__,
            WorkspaceMembership.__table__,
            UserMemory.__table__,
        ],
    )
    return create_session_factory(engine)()


def test_propose_approve_and_injection_text() -> None:
    session = _session()
    workspace = WorkspaceRepository(session).create(name="MemProj")
    user = UserRepository(session).create_user(
        email="mem-user@example.com",
        display_name="Mem User",
        system_role="user",
    )
    WorkspaceMembershipRepository(session).upsert_membership(
        workspace_id=workspace.id,
        user_id=user.id,
        role="contributor",
    )
    session.commit()

    proposed = user_memory.propose_memory(
        session,
        user_id=user.id,
        workspace_id=workspace.id,
        content="  Prefers Spanish answers  ",
    )
    assert proposed.status == "proposed"
    assert proposed.content == "Prefers Spanish answers"

    # Not injected until approved
    assert (
        user_memory.approved_injection_text(
            session, user_id=user.id, workspace_id=workspace.id
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
        session, user_id=user.id, workspace_id=workspace.id
    )
    assert "User memory (approved):" in injection
    assert "Prefers Spanish answers" in injection


def test_reject_blocks_injection_until_restored() -> None:
    session = _session()
    user = UserRepository(session).create_user(
        email="mem-user-2@example.com",
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

    restored = user_memory.approve_memory(
        session,
        memory_id=memory.id,
        reviewer_user_id=user.id,
        owner_user_id=user.id,
    )
    assert restored.status == "approved"
    assert "Remember my timezone is UTC" in user_memory.approved_injection_text(
        session, user_id=user.id
    )

    try:
        user_memory.approve_memory(
            session,
            memory_id=memory.id,
            reviewer_user_id=user.id,
            owner_user_id=user.id,
        )
        raise AssertionError("expected conflict on already-approved")
    except user_memory.UserMemoryError as exc:
        assert exc.status_code == 409


def test_empty_content_rejected() -> None:
    session = _session()
    user = UserRepository(session).create_user(
        email="mem-user-3@example.com",
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
    owner = users.create_user(email="owner@example.com", display_name="Owner")
    other = users.create_user(email="other@example.com", display_name="Other")
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


def test_global_and_workspace_scope_injection() -> None:
    session = _session()
    workspace = WorkspaceRepository(session).create(name="Scoped")
    user = UserRepository(session).create_user(
        email="scoped@example.com",
        display_name="Scoped",
    )
    WorkspaceMembershipRepository(session).upsert_membership(
        workspace_id=workspace.id,
        user_id=user.id,
        role="viewer",
    )
    global_mem = user_memory.propose_memory(
        session, user_id=user.id, content="Global preference"
    )
    workspace_mem = user_memory.propose_memory(
        session,
        user_id=user.id,
        workspace_id=workspace.id,
        content="Workspace preference",
    )
    for mem in (global_mem, workspace_mem):
        user_memory.approve_memory(
            session,
            memory_id=mem.id,
            reviewer_user_id=user.id,
            owner_user_id=user.id,
        )

    text = user_memory.approved_injection_text(
        session, user_id=user.id, workspace_id=workspace.id
    )
    assert "Global preference" in text
    assert "Workspace preference" in text

    global_only = user_memory.approved_injection_text(session, user_id=user.id)
    assert "Global preference" in global_only
    # Without workspace filter, workspace-scoped rows are still listed
    # when workspace_id is None (list_for_user only filters by workspace
    # when workspace_id is provided).


def test_propose_workspace_scoped_requires_membership() -> None:
    session = _session()
    workspace = WorkspaceRepository(session).create(name="Foreign")
    user = UserRepository(session).create_user(
        email="outsider@example.com",
        display_name="Outsider",
        system_role="user",
    )
    try:
        user_memory.propose_memory(
            session,
            user_id=user.id,
            workspace_id=workspace.id,
            content="Should not land on foreign workspace",
        )
        raise AssertionError("expected workspace access denied")
    except user_memory.UserMemoryError as exc:
        assert exc.status_code == 403
        assert exc.detail == "workspace access required"


def test_approve_workspace_scoped_requires_membership() -> None:
    session = _session()
    workspace = WorkspaceRepository(session).create(name="Was Member")
    user = UserRepository(session).create_user(
        email="ex-member@example.com",
        display_name="Ex Member",
        system_role="user",
    )
    memberships = WorkspaceMembershipRepository(session)
    memberships.upsert_membership(
        workspace_id=workspace.id,
        user_id=user.id,
        role="contributor",
    )
    proposed = user_memory.propose_memory(
        session,
        user_id=user.id,
        workspace_id=workspace.id,
        content="Workspace fact",
    )
    # Membership revoked before self-approve (would inject into system prompt).
    assert memberships.remove_membership(workspace_id=workspace.id, user_id=user.id)
    session.flush()

    try:
        user_memory.approve_memory(
            session,
            memory_id=proposed.id,
            reviewer_user_id=user.id,
            owner_user_id=user.id,
        )
        raise AssertionError("expected workspace access denied on approve")
    except user_memory.UserMemoryError as exc:
        assert exc.status_code == 403
        assert exc.detail == "workspace access required"

    assert (
        user_memory.approved_injection_text(
            session, user_id=user.id, workspace_id=workspace.id
        )
        == ""
    )


def test_superadmin_can_propose_and_approve_without_membership() -> None:
    session = _session()
    workspace = WorkspaceRepository(session).create(name="Admin Scope")
    admin = UserRepository(session).create_user(
        email="super@example.com",
        display_name="Super",
        system_role="superadmin",
    )
    proposed = user_memory.propose_memory(
        session,
        user_id=admin.id,
        workspace_id=workspace.id,
        content="Superadmin note",
        is_superadmin=True,
    )
    approved = user_memory.approve_memory(
        session,
        memory_id=proposed.id,
        reviewer_user_id=admin.id,
        owner_user_id=admin.id,
        is_superadmin=True,
    )
    assert approved.status == "approved"


def test_update_proposed_memory_content() -> None:
    session = _session()
    user = UserRepository(session).create_user(
        email="edit-user@example.com",
        display_name="Edit",
        system_role="user",
    )
    proposed = user_memory.propose_memory(
        session, user_id=user.id, content="Original preference"
    )
    updated = user_memory.update_proposed_memory(
        session,
        memory_id=proposed.id,
        content="  Revised preference  ",
        owner_user_id=user.id,
    )
    assert updated.content == "Revised preference"
    assert updated.status == "proposed"

    approved = user_memory.approve_memory(
        session,
        memory_id=proposed.id,
        reviewer_user_id=user.id,
        owner_user_id=user.id,
    )
    try:
        user_memory.update_proposed_memory(
            session,
            memory_id=approved.id,
            content="Too late",
            owner_user_id=user.id,
        )
        raise AssertionError("expected conflict on approved edit")
    except user_memory.UserMemoryError as exc:
        assert exc.status_code == 409


def test_reject_approved_removes_injection() -> None:
    session = _session()
    user = UserRepository(session).create_user(
        email="soft-remove@example.com",
        display_name="Soft",
        system_role="user",
    )
    proposed = user_memory.propose_memory(
        session, user_id=user.id, content="Temporary preference"
    )
    user_memory.approve_memory(
        session,
        memory_id=proposed.id,
        reviewer_user_id=user.id,
        owner_user_id=user.id,
    )
    assert "Temporary preference" in user_memory.approved_injection_text(
        session, user_id=user.id
    )

    rejected = user_memory.reject_memory(
        session,
        memory_id=proposed.id,
        reviewer_user_id=user.id,
        owner_user_id=user.id,
    )
    assert rejected.status == "rejected"
    assert user_memory.approved_injection_text(session, user_id=user.id) == ""


def test_approve_rejected_restores_injection() -> None:
    session = _session()
    user = UserRepository(session).create_user(
        email="soft-restore@example.com",
        display_name="Restore",
        system_role="user",
    )
    proposed = user_memory.propose_memory(
        session, user_id=user.id, content="Keep this preference"
    )
    user_memory.approve_memory(
        session,
        memory_id=proposed.id,
        reviewer_user_id=user.id,
        owner_user_id=user.id,
    )
    user_memory.reject_memory(
        session,
        memory_id=proposed.id,
        reviewer_user_id=user.id,
        owner_user_id=user.id,
    )
    assert user_memory.approved_injection_text(session, user_id=user.id) == ""

    restored = user_memory.approve_memory(
        session,
        memory_id=proposed.id,
        reviewer_user_id=user.id,
        owner_user_id=user.id,
    )
    assert restored.status == "approved"
    assert "Keep this preference" in user_memory.approved_injection_text(
        session, user_id=user.id
    )


def test_injection_text_caps_at_max_items() -> None:
    session = _session()
    user = UserRepository(session).create_user(
        email="cap-user@example.com",
        display_name="Cap",
        system_role="user",
    )
    for index in range(10):
        memory = user_memory.propose_memory(
            session, user_id=user.id, content=f"Preference {index}"
        )
        user_memory.approve_memory(
            session,
            memory_id=memory.id,
            reviewer_user_id=user.id,
            owner_user_id=user.id,
        )

    text = user_memory.approved_injection_text(session, user_id=user.id)
    assert text.startswith("User memory (approved):\n")
    injected_lines = text.splitlines()[1:]
    assert len(injected_lines) == 8


def test_special_characters_roundtrip_and_injection() -> None:
    session = _session()
    user = UserRepository(session).create_user(
        email="unicode-user@example.com",
        display_name="Unicode",
        system_role="user",
    )
    content = 'Prefers "español" 🌍\nSecond line <script>alert(1)</script> & símbolos'
    memory = user_memory.propose_memory(session, user_id=user.id, content=content)
    assert memory.content == content

    user_memory.approve_memory(
        session,
        memory_id=memory.id,
        reviewer_user_id=user.id,
        owner_user_id=user.id,
    )
    text = user_memory.approved_injection_text(session, user_id=user.id)
    assert '"español" 🌍' in text
    assert "<script>alert(1)</script>" in text
