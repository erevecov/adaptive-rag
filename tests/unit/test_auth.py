"""Unit tests for local authentication and project RBAC helpers."""

from __future__ import annotations

import hashlib
from uuid import uuid4

import pytest

from adaptive_rag.auth import (
    PROJECT_ROLE_RANK,
    CurrentPrincipal,
    get_project_role,
    hash_access_token,
    role_meets,
    users_exist,
)
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Project, ProjectMembership, User
from adaptive_rag.db.repositories import ProjectRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            User.__table__,
            ProjectMembership.__table__,
        ],
    )
    return create_session_factory(engine)()


def _user(
    *,
    login: str = "alice",
    display_name: str = "Alice",
    system_role: str = "user",
) -> User:
    user = User(login=login, display_name=display_name, system_role=system_role)
    user.id = uuid4()
    return user


def test_hash_access_token_is_stable_and_prefixed() -> None:
    digest = hashlib.sha256(b"secret-token").hexdigest()

    assert hash_access_token("secret-token") == f"sha256:{digest}"
    assert hash_access_token("secret-token") == hash_access_token("secret-token")


def test_hash_access_token_strips_surrounding_whitespace() -> None:
    assert hash_access_token("  secret-token  ") == hash_access_token("secret-token")


@pytest.mark.parametrize("raw", ["", "   ", "\n\t"])
def test_hash_access_token_rejects_empty_token(raw: str) -> None:
    with pytest.raises(ValueError, match="access_token must not be empty"):
        hash_access_token(raw)


def test_bootstrap_principal_reports_superadmin_identity() -> None:
    principal = CurrentPrincipal(user=None, is_bootstrap=True)

    assert principal.user_id is None
    assert principal.login == "bootstrap"
    assert principal.display_name == "Bootstrap Superadmin"
    assert principal.system_role == "superadmin"
    assert principal.is_superadmin is True


def test_user_principal_delegates_to_user_fields() -> None:
    user = _user(login="bob", display_name="Bob", system_role="user")
    principal = CurrentPrincipal(user=user)

    assert principal.user_id == user.id
    assert principal.login == "bob"
    assert principal.display_name == "Bob"
    assert principal.system_role == "user"
    assert principal.is_superadmin is False


def test_user_principal_superadmin_role_is_superadmin() -> None:
    user = _user(system_role="superadmin")
    principal = CurrentPrincipal(user=user)

    assert principal.is_bootstrap is False
    assert principal.is_superadmin is True


def test_get_project_role_returns_superadmin_without_touching_session() -> None:
    principal = CurrentPrincipal(user=None, is_bootstrap=True)

    # A non-Session sentinel proves the superadmin branch never queries.
    role = get_project_role(
        object(),  # type: ignore[arg-type]
        principal=principal,
        project_id=uuid4(),
    )

    assert role == "superadmin"


@pytest.mark.parametrize(
    ("role", "minimum_role", "expected"),
    [
        ("superadmin", "admin", True),
        ("admin", "viewer", True),
        ("admin", "admin", True),
        ("contributor", "contributor", True),
        ("contributor", "admin", False),
        ("viewer", "contributor", False),
        ("viewer", "viewer", True),
        (None, "viewer", False),
    ],
)
def test_role_meets_respects_rank_ordering(
    role: str | None, minimum_role: str, expected: bool
) -> None:
    assert role_meets(role, minimum_role) is expected


def test_project_role_rank_is_strictly_increasing() -> None:
    assert (
        PROJECT_ROLE_RANK["viewer"]
        < PROJECT_ROLE_RANK["contributor"]
        < PROJECT_ROLE_RANK["admin"]
    )


def test_users_exist_reflects_persisted_rows() -> None:
    session = _make_session()

    assert users_exist(session) is False

    user = _user()
    session.add(user)
    session.commit()

    assert users_exist(session) is True


def test_get_project_role_returns_membership_role_for_regular_user() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="Docs")
    user = _user(system_role="user")
    session.add(user)
    session.flush()
    session.add(
        ProjectMembership(
            project_id=project.id, user_id=user.id, role="contributor"
        )
    )
    session.commit()

    principal = CurrentPrincipal(user=user)

    assert (
        get_project_role(session, principal=principal, project_id=project.id)
        == "contributor"
    )


def test_get_project_role_returns_none_without_membership() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="Docs")
    user = _user(system_role="user")
    session.add(user)
    session.commit()

    principal = CurrentPrincipal(user=user)

    assert (
        get_project_role(session, principal=principal, project_id=project.id) is None
    )


def test_users_exist_fails_closed_on_operational_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    import pytest
    from sqlalchemy.exc import OperationalError

    from adaptive_rag import auth as auth_module

    class _RaisingScalarSession:
        def __init__(self) -> None:
            self.rolled_back = False

        def scalar(self, statement: object) -> int:
            raise OperationalError("SELECT count(*)", {}, Exception("connection reset"))

        def rollback(self) -> None:
            self.rolled_back = True

    session = _RaisingScalarSession()

    with (
        caplog.at_level(logging.WARNING, logger=auth_module.__name__),
        pytest.raises(OperationalError),
    ):
        auth_module.users_exist(session)  # type: ignore[arg-type]

    assert session.rolled_back is True
    records = [
        record
        for record in caplog.records
        if record.name == auth_module.__name__
        and "users_exist_check_failed" in record.getMessage()
    ]
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING
    assert "refusing bootstrap fail-open" in records[0].getMessage()
    assert records[0].exc_info is not None
    assert records[0].exc_info[0] is OperationalError

