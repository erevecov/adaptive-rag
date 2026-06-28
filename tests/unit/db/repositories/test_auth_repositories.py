"""Tests para repositories locales de usuarios y memberships de proyecto."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Project, ProjectMembership, User, UserAccessToken
from adaptive_rag.db.repositories import (
    ProjectMembershipRepository,
    ProjectRepository,
    UserRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            User.__table__,
            UserAccessToken.__table__,
            ProjectMembership.__table__,
        ],
    )
    return create_session_factory(engine)()


def _create_project(session, name: str = "demo") -> Project:
    return ProjectRepository(session).create(name=name)


def test_user_repository_create_flushes_without_committing() -> None:
    session = _make_session()
    user = UserRepository(session).create_user(
        login="Owner@Example.com ",
        display_name="Owner",
        system_role="superadmin",
    )
    user_id = user.id

    assert user.login == "owner@example.com"
    assert user.system_role == "superadmin"
    assert user_id is not None

    session.rollback()
    session.expunge_all()

    assert UserRepository(session).get_user(user_id) is None


def test_user_repository_rejects_duplicate_login() -> None:
    session = _make_session()
    repo = UserRepository(session)
    repo.create_user(login="viewer@example.com", display_name="Viewer")
    session.commit()

    with pytest.raises(ValueError, match="user_login_already_exists"):
        repo.create_user(login=" VIEWER@example.com ", display_name="Duplicate")


def test_user_repository_lists_users_by_login() -> None:
    session = _make_session()
    repo = UserRepository(session)
    repo.create_user(login="z@example.com", display_name="Zed")
    repo.create_user(login="a@example.com", display_name="Ada")
    repo.create_user(login="m@example.com", display_name="Mia")
    session.commit()

    users = repo.list_users()

    assert [user.login for user in users] == [
        "a@example.com",
        "m@example.com",
        "z@example.com",
    ]


def test_user_repository_updates_user_fields() -> None:
    session = _make_session()
    repo = UserRepository(session)
    user = repo.create_user(login="member@example.com", display_name="Member")
    session.commit()

    updated = repo.update_user(
        user.id,
        display_name="Member Two",
        system_role="superadmin",
        is_active=False,
    )

    assert updated is not None
    assert updated.display_name == "Member Two"
    assert updated.system_role == "superadmin"
    assert updated.is_active is False


def test_user_repository_upserts_token_hash_and_can_revoke() -> None:
    session = _make_session()
    repo = UserRepository(session)
    user = repo.create_user(login="token@example.com", display_name="Token")
    expires_at = datetime(2026, 1, 1, tzinfo=UTC)
    token = repo.upsert_access_token(
        user_id=user.id,
        token_hash="sha256:first",
        label="Initial",
        expires_at=expires_at,
    )
    session.commit()

    updated = repo.upsert_access_token(
        user_id=user.id,
        token_hash="sha256:first",
        label="Updated",
        expires_at=None,
    )

    assert updated.id == token.id
    assert updated.token_hash == "sha256:first"
    assert updated.label == "Updated"
    assert updated.expires_at is None
    assert repo.get_user_by_token_hash("sha256:first") == user
    assert repo.get_user_by_token_hash("plaintext-token") is None
    assert repo.revoke_access_token("sha256:first") is True
    assert repo.get_user_by_token_hash("sha256:first") is None
    assert repo.revoke_access_token("missing") is False


def test_user_repository_rejects_token_for_missing_user() -> None:
    session = _make_session()

    with pytest.raises(ValueError, match="user_not_found"):
        UserRepository(session).upsert_access_token(
            user_id=uuid4(),
            token_hash="sha256:missing",
        )


def test_project_membership_repository_creates_and_updates_role() -> None:
    session = _make_session()
    project = _create_project(session)
    user = UserRepository(session).create_user(
        login="admin@example.com",
        display_name="Admin",
    )
    repo = ProjectMembershipRepository(session)

    membership = repo.upsert_membership(
        project_id=project.id,
        user_id=user.id,
        role="VIEWER",
    )
    updated = repo.upsert_membership(
        project_id=project.id,
        user_id=user.id,
        role="admin",
    )

    assert updated.id == membership.id
    assert updated.role == "admin"
    assert repo.get_membership(project_id=project.id, user_id=user.id) == updated


def test_project_membership_repository_rejects_unsupported_role() -> None:
    session = _make_session()
    project = _create_project(session)
    user = UserRepository(session).create_user(
        login="bad-role@example.com",
        display_name="Bad Role",
    )

    with pytest.raises(ValueError, match="unsupported project role: owner"):
        ProjectMembershipRepository(session).upsert_membership(
            project_id=project.id,
            user_id=user.id,
            role="owner",
        )


def test_project_membership_repository_lists_deterministic_orders() -> None:
    session = _make_session()
    project = _create_project(session)
    other_project = _create_project(session, "other")
    user_repo = UserRepository(session)
    bob = user_repo.create_user(login="bob@example.com", display_name="Bob")
    ada = user_repo.create_user(login="ada@example.com", display_name="Ada")
    mia = user_repo.create_user(login="mia@example.com", display_name="Mia")
    repo = ProjectMembershipRepository(session)
    repo.upsert_membership(project_id=project.id, user_id=bob.id, role="viewer")
    repo.upsert_membership(project_id=project.id, user_id=ada.id, role="admin")
    repo.upsert_membership(project_id=other_project.id, user_id=mia.id, role="viewer")
    repo.upsert_membership(project_id=project.id, user_id=mia.id, role="contributor")
    session.commit()

    project_members = repo.list_project_members(project_id=project.id)
    user_memberships = repo.list_user_memberships(user_id=mia.id)

    assert [member.user_id for member in project_members] == [ada.id, bob.id, mia.id]
    assert [membership.project_id for membership in user_memberships] == sorted(
        [project.id, other_project.id],
        key=str,
    )


def test_project_membership_repository_removes_membership() -> None:
    session = _make_session()
    project = _create_project(session)
    user = UserRepository(session).create_user(
        login="remove@example.com",
        display_name="Remove",
    )
    repo = ProjectMembershipRepository(session)
    repo.upsert_membership(project_id=project.id, user_id=user.id, role="viewer")
    session.commit()

    assert repo.remove_membership(project_id=project.id, user_id=user.id) is True
    assert repo.get_membership(project_id=project.id, user_id=user.id) is None
    assert repo.remove_membership(project_id=project.id, user_id=user.id) is False

