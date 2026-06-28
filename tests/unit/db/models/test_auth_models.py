"""Tests for M37 local auth and project membership models."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Project, ProjectMembership, User, UserAccessToken
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


def _assert_integrity_error(session) -> None:
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
    else:
        raise AssertionError("Expected IntegrityError")


def test_user_defaults_to_active_regular_user() -> None:
    session = _make_session()
    user = User(login="viewer@example.com", display_name="Viewer")

    session.add(user)
    session.commit()

    assert user.system_role == "user"
    assert user.is_active is True
    assert user.created_at is not None
    assert user.updated_at is not None


def test_user_rejects_unsupported_system_role() -> None:
    session = _make_session()
    session.add(
        User(
            login="bad@example.com",
            display_name="Bad",
            system_role="owner",
        )
    )

    _assert_integrity_error(session)


def test_user_login_is_unique() -> None:
    session = _make_session()
    session.add_all(
        [
            User(login="same@example.com", display_name="First"),
            User(login="same@example.com", display_name="Second"),
        ]
    )

    _assert_integrity_error(session)


def test_user_access_token_stores_hash_not_plaintext() -> None:
    session = _make_session()
    user = User(login="token@example.com", display_name="Token User")
    session.add(user)
    session.flush()
    token = UserAccessToken(
        user_id=user.id,
        token_hash="sha256:abc",
        label="local dev token",
        expires_at=datetime(2026, 7, 1, tzinfo=UTC),
    )

    session.add(token)
    session.commit()

    columns = {column.name: column for column in inspect(UserAccessToken).columns}
    assert token.id is not None
    assert token.token_hash == "sha256:abc"
    assert token.revoked_at is None
    assert columns["token_hash"].nullable is False
    assert "token_value" not in columns
    assert "plaintext_token" not in columns


def test_project_membership_persists_single_role_per_project_user() -> None:
    session = _make_session()
    project = Project(name="demo")
    user = User(login="admin@example.com", display_name="Admin")
    session.add_all([project, user])
    session.flush()
    membership = ProjectMembership(
        project_id=project.id,
        user_id=user.id,
        role="admin",
    )

    session.add(membership)
    session.commit()

    assert membership.id is not None
    assert membership.role == "admin"

    session.add(
        ProjectMembership(
            project_id=project.id,
            user_id=user.id,
            role="viewer",
        )
    )
    _assert_integrity_error(session)


def test_project_membership_rejects_unsupported_role() -> None:
    session = _make_session()
    project = Project(name="demo")
    user = User(login="bad-role@example.com", display_name="Bad Role")
    session.add_all([project, user])
    session.flush()
    session.add(
        ProjectMembership(
            project_id=project.id,
            user_id=user.id,
            role="superadmin",
        )
    )

    _assert_integrity_error(session)

