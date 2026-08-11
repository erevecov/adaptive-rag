"""HTTP contract tests for local human authentication."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import get_session
from adaptive_rag.config.settings import get_settings
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    LoginAttempt,
    User,
    UserAccessToken,
    UserPasswordCredential,
    UserSession,
    Workspace,
    WorkspaceMembership,
)
from adaptive_rag.db.repositories import (
    HumanAuthRepository,
    UserRepository,
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)
from adaptive_rag.security.human_auth import PasswordService

ORIGIN = "http://localhost:5173"


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Workspace.__table__,
            User.__table__,
            UserAccessToken.__table__,
            UserPasswordCredential.__table__,
            UserSession.__table__,
            LoginAttempt.__table__,
            WorkspaceMembership.__table__,
        ],
    )
    return Session(engine, expire_on_commit=False)


@pytest.fixture
def session() -> Iterator[Session]:
    active = _make_session()
    try:
        yield active
    finally:
        active.close()


@pytest.fixture
def client(session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("ADAPTIVE_RAG_BOOTSTRAP_SECRET", "setup-secret-value")
    monkeypatch.setenv("ADAPTIVE_RAG_ENV", "test")
    get_settings.cache_clear()
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def _setup(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/auth/setup",
        headers={"X-Setup-Secret": "setup-secret-value"},
        json={
            "email": "Root@Example.com",
            "display_name": "Root",
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _login(
    client: TestClient,
    *,
    email: str = "root@example.com",
    password: str = "correct horse battery staple",
) -> dict[str, object]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def _csrf_headers(client: TestClient) -> dict[str, str]:
    response = client.get("/auth/csrf")
    assert response.status_code == 200, response.text
    return {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}


def test_empty_installation_fails_closed_and_setup_requires_secret(
    client: TestClient,
) -> None:
    unauthenticated = client.get("/auth/me")
    missing_secret = client.post(
        "/auth/setup",
        json={
            "email": "root@example.com",
            "display_name": "Root",
            "password": "correct horse battery staple",
        },
    )

    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["detail"]["code"] == "authentication_required"
    assert missing_secret.status_code == 403
    assert missing_secret.json()["detail"]["code"] == "invalid_setup_secret"


def test_setup_creates_first_superadmin_with_argon2_credential_once(
    client: TestClient, session: Session
) -> None:
    payload = _setup(client)
    duplicate = client.post(
        "/auth/setup",
        headers={"X-Setup-Secret": "setup-secret-value"},
        json={
            "email": "other@example.com",
            "display_name": "Other",
            "password": "another correct horse password",
        },
    )

    user = UserRepository(session).get_by_email("root@example.com")
    assert payload["email"] == "root@example.com"
    assert payload["system_role"] == "superadmin"
    assert user is not None
    credential = HumanAuthRepository(session).get_credential(user.id)
    assert credential is not None
    assert credential.password_hash.startswith("$argon2id$")
    assert "correct horse" not in credential.password_hash
    assert credential.must_change_password is False
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "setup_already_complete"


def test_login_cookie_resolves_me_and_invalid_login_is_generic(
    client: TestClient,
) -> None:
    _setup(client)
    invalid = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "wrong password value"},
    )
    payload = _login(client, email=" ROOT@example.com ")
    me = client.get("/auth/me")

    assert invalid.status_code == 401
    assert invalid.json()["detail"]["code"] == "invalid_credentials"
    assert payload["must_change_password"] is False
    cookie = client.cookies.get("adaptive_rag_session")
    assert cookie is not None
    set_cookie = (
        client.post(
            "/auth/login",
            json={
                "email": "root@example.com",
                "password": "correct horse battery staple",
            },
        )
        .headers["set-cookie"]
        .lower()
    )
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert me.status_code == 200
    assert me.json()["email"] == "root@example.com"


def test_login_is_rate_limited_by_hashed_identifier(client: TestClient) -> None:
    _setup(client)

    responses = [
        client.post(
            "/auth/login",
            json={
                "email": "root@example.com",
                "password": "incorrect password value",
            },
        )
        for _ in range(11)
    ]

    assert [response.status_code for response in responses[:10]] == [401] * 10
    assert responses[-1].status_code == 429
    assert responses[-1].json()["detail"]["code"] == "rate_limited"


def test_login_rate_limit_does_not_lock_account_from_other_client_ips(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(client)
    monkeypatch.setenv("ADAPTIVE_RAG_AUTH_LOGIN_MAX_ATTEMPTS_PER_EMAIL", "3")
    get_settings.cache_clear()

    for _ in range(3):
        failed = client.post(
            "/auth/login",
            json={
                "email": "root@example.com",
                "password": "incorrect password value",
            },
        )
        assert failed.status_code == 401

    blocked_same_ip = client.post(
        "/auth/login",
        json={
            "email": "root@example.com",
            "password": "correct horse battery staple",
        },
    )
    assert blocked_same_ip.status_code == 429

    # Simulate a different client network by rewriting recorded IP hashes.
    for attempt in session.scalars(select(LoginAttempt)).all():
        attempt.ip_hash = "sha256:foreign-network"
    session.commit()

    allowed_other_ip = client.post(
        "/auth/login",
        json={
            "email": "root@example.com",
            "password": "correct horse battery staple",
        },
    )
    assert allowed_other_ip.status_code == 200, allowed_other_ip.text
    get_settings.cache_clear()


def test_cookie_mutation_requires_allowed_origin_and_session_csrf(
    client: TestClient,
) -> None:
    _setup(client)
    _login(client)

    missing = client.patch("/auth/me/preferences", json={"last_workspace_id": None})
    bad_origin = client.patch(
        "/auth/me/preferences",
        headers={**_csrf_headers(client), "Origin": "https://evil.example"},
        json={"last_workspace_id": None},
    )
    allowed = client.patch(
        "/auth/me/preferences",
        headers=_csrf_headers(client),
        json={"last_workspace_id": None},
    )

    assert missing.status_code == 403
    assert missing.json()["detail"]["code"] == "csrf_failed"
    assert bad_origin.status_code == 403
    assert bad_origin.json()["detail"]["code"] == "csrf_failed"
    assert allowed.status_code == 200


def test_mandatory_password_change_blocks_app_and_revokes_other_sessions(
    client: TestClient, session: Session
) -> None:
    user = UserRepository(session).create_user(
        email="member@example.com", display_name="Member"
    )
    HumanAuthRepository(session).set_password(
        user_id=user.id,
        password_hash=PasswordService().hash("temporary correct horse password"),
        must_change_password=True,
    )
    session.commit()

    _login(
        client,
        email="member@example.com",
        password="temporary correct horse password",
    )
    first_cookie = client.cookies.get("adaptive_rag_session")
    second_client = TestClient(client.app)
    _login(
        second_client,
        email="member@example.com",
        password="temporary correct horse password",
    )
    blocked = client.get("/workspaces")
    changed = client.post(
        "/auth/change-password",
        headers=_csrf_headers(client),
        json={"new_password": "permanent correct horse password"},
    )
    old_login = client.post(
        "/auth/login",
        json={
            "email": "member@example.com",
            "password": "temporary correct horse password",
        },
    )
    revoked_me = second_client.get("/auth/me")

    assert first_cookie is not None
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "password_change_required"
    assert changed.status_code == 200
    assert changed.json()["must_change_password"] is False
    assert old_login.status_code == 401
    assert revoked_me.status_code == 401
    second_client.close()


def test_logout_revokes_session_and_clears_cookie(client: TestClient) -> None:
    _setup(client)
    _login(client)

    response = client.post("/auth/logout", headers=_csrf_headers(client))
    me = client.get("/auth/me")

    assert response.status_code == 204
    assert client.cookies.get("adaptive_rag_session") is None
    assert me.status_code == 401


def test_cookie_session_fails_closed_for_an_inactive_user(
    client: TestClient, session: Session
) -> None:
    root = _setup(client)
    _login(client)
    UserRepository(session).update_user(UUID(str(root["id"])), is_active=False)
    session.commit()

    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "authentication_required"


def test_superadmin_creates_user_atomically_and_password_is_returned_once(
    client: TestClient, session: Session
) -> None:
    _setup(client)
    _login(client)
    workspace = WorkspaceRepository(session).create(name="Workspace One")
    session.commit()

    response = client.post(
        "/admin/users",
        headers=_csrf_headers(client),
        json={
            "email": "Member@Example.com",
            "display_name": "Member",
            "system_role": "user",
            "initial_workspace_id": str(workspace.id),
            "initial_workspace_role": "viewer",
        },
    )
    listed = client.get("/admin/users")

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["user"]["email"] == "member@example.com"
    assert len(payload["temporary_password"]) >= 43
    assert response.headers["cache-control"] == "no-store"
    member = UserRepository(session).get_by_email("member@example.com")
    assert member is not None
    credential = HumanAuthRepository(session).get_credential(member.id)
    membership = WorkspaceMembershipRepository(session).get_membership(
        workspace_id=workspace.id, user_id=member.id
    )
    assert credential is not None and credential.must_change_password is True
    assert membership is not None and membership.role == "viewer"
    assert "temporary_password" not in listed.text
    listed_member = next(
        item for item in listed.json()["items"] if item["email"] == "member@example.com"
    )
    assert listed_member["memberships"][0]["role"] == "viewer"


def test_ordinary_user_requires_initial_membership_and_superadmin_forbids_it(
    client: TestClient, session: Session
) -> None:
    _setup(client)
    _login(client)
    workspace = WorkspaceRepository(session).create(name="Workspace")
    session.commit()

    ordinary = client.post(
        "/admin/users",
        headers=_csrf_headers(client),
        json={
            "email": "ordinary@example.com",
            "display_name": "Ordinary",
            "system_role": "user",
        },
    )
    global_admin = client.post(
        "/admin/users",
        headers=_csrf_headers(client),
        json={
            "email": "global@example.com",
            "display_name": "Global",
            "system_role": "superadmin",
            "initial_workspace_id": str(workspace.id),
            "initial_workspace_role": "admin",
        },
    )

    assert ordinary.status_code == 422
    assert ordinary.json()["detail"]["code"] == "initial_membership_required"
    assert global_admin.status_code == 422
    assert global_admin.json()["detail"]["code"] == "superadmin_membership_forbidden"


def test_last_active_superadmin_is_protected_and_user_can_be_reactivated(
    client: TestClient, session: Session
) -> None:
    root_payload = _setup(client)
    _login(client)
    root_id = root_payload["id"]

    blocked = client.post(
        f"/admin/users/{root_id}/suspend", headers=_csrf_headers(client)
    )
    created = client.post(
        "/admin/users",
        headers=_csrf_headers(client),
        json={
            "email": "second-root@example.com",
            "display_name": "Second Root",
            "system_role": "superadmin",
        },
    )
    allowed = client.post(
        f"/admin/users/{root_id}/suspend", headers=_csrf_headers(client)
    )
    root = UserRepository(session).get_user(UUID(str(root_payload["id"])))

    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "last_active_superadmin"
    assert created.status_code == 201
    assert allowed.status_code == 200
    assert root is not None and root.is_active is False


def test_last_active_superadmin_cannot_be_demoted(client: TestClient) -> None:
    root_payload = _setup(client)
    _login(client)

    response = client.patch(
        f"/admin/users/{root_payload['id']}",
        headers=_csrf_headers(client),
        json={"system_role": "user"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "last_active_superadmin"


def test_password_reset_suspension_and_reactivation_revoke_sessions(
    client: TestClient, session: Session
) -> None:
    _setup(client)
    _login(client)
    workspace = WorkspaceRepository(session).create(name="Managed")
    session.commit()
    created = client.post(
        "/admin/users",
        headers=_csrf_headers(client),
        json={
            "email": "managed@example.com",
            "display_name": "Managed User",
            "system_role": "user",
            "initial_workspace_id": str(workspace.id),
            "initial_workspace_role": "viewer",
        },
    ).json()
    user_id = created["user"]["id"]

    member_client = TestClient(client.app)
    _login(
        member_client,
        email="managed@example.com",
        password=created["temporary_password"],
    )
    changed = member_client.post(
        "/auth/change-password",
        headers=_csrf_headers(member_client),
        json={"new_password": "managed permanent horse password"},
    )
    reset = client.post(
        f"/admin/users/{user_id}/reset-password",
        headers=_csrf_headers(client),
    )
    revoked_after_reset = member_client.get("/auth/me")
    suspended = client.post(
        f"/admin/users/{user_id}/suspend", headers=_csrf_headers(client)
    )
    suspended_login = client.post(
        "/auth/login",
        json={
            "email": "managed@example.com",
            "password": reset.json()["temporary_password"],
        },
    )
    reactivated = client.post(
        f"/admin/users/{user_id}/reactivate", headers=_csrf_headers(client)
    )

    assert changed.status_code == 200
    assert reset.status_code == 200
    assert reset.headers["cache-control"] == "no-store"
    assert reset.json()["user"]["must_change_password"] is True
    assert revoked_after_reset.status_code == 401
    assert suspended.status_code == 200
    assert suspended.json()["is_active"] is False
    assert suspended_login.status_code == 401
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True
    member_client.close()


def test_workspace_admin_adds_existing_user_by_email_with_isolated_roles(
    client: TestClient, session: Session
) -> None:
    _setup(client)
    _login(client)
    first = WorkspaceRepository(session).create(name="First")
    second = WorkspaceRepository(session).create(name="Second")
    session.commit()

    admin_created = client.post(
        "/admin/users",
        headers=_csrf_headers(client),
        json={
            "email": "admin@example.com",
            "display_name": "Admin",
            "system_role": "user",
            "initial_workspace_id": str(first.id),
            "initial_workspace_role": "admin",
        },
    ).json()
    viewer_created = client.post(
        "/admin/users",
        headers=_csrf_headers(client),
        json={
            "email": "viewer@example.com",
            "display_name": "Viewer",
            "system_role": "user",
            "initial_workspace_id": str(second.id),
            "initial_workspace_role": "viewer",
        },
    ).json()
    client.cookies.clear()
    _login(
        client,
        email="admin@example.com",
        password=admin_created["temporary_password"],
    )
    changed = client.post(
        "/auth/change-password",
        headers=_csrf_headers(client),
        json={"new_password": "admin permanent horse password"},
    )
    added = client.post(
        f"/workspaces/{first.id}/members",
        headers=_csrf_headers(client),
        json={"email": "VIEWER@example.com", "role": "contributor"},
    )
    foreign = client.get(f"/workspaces/{second.id}/members")
    self_remove = client.delete(
        f"/workspaces/{first.id}/members/{admin_created['user']['id']}",
        headers=_csrf_headers(client),
    )

    viewer_id = UUID(viewer_created["user"]["id"])
    first_role = WorkspaceMembershipRepository(session).get_membership(
        workspace_id=first.id, user_id=viewer_id
    )
    second_role = WorkspaceMembershipRepository(session).get_membership(
        workspace_id=second.id, user_id=viewer_id
    )
    assert changed.status_code == 200
    assert added.status_code == 201, added.text
    assert added.json()["role"] == "contributor"
    assert foreign.status_code == 403
    assert self_remove.status_code == 409
    assert self_remove.json()["detail"]["code"] == ("last_active_workspace_admin")
    assert first_role is not None and first_role.role == "contributor"
    assert second_role is not None and second_role.role == "viewer"


def test_legacy_membership_routes_protect_last_workspace_admin(
    client: TestClient, session: Session
) -> None:
    _setup(client)
    _login(client)
    workspace = WorkspaceRepository(session).create(name="Legacy Guard")
    created = client.post(
        "/admin/users",
        headers=_csrf_headers(client),
        json={
            "email": "solo-admin@example.com",
            "display_name": "Solo Admin",
            "system_role": "user",
            "initial_workspace_id": str(workspace.id),
            "initial_workspace_role": "admin",
        },
    ).json()
    client.cookies.clear()
    _login(
        client,
        email="solo-admin@example.com",
        password=created["temporary_password"],
    )
    client.post(
        "/auth/change-password",
        headers=_csrf_headers(client),
        json={"new_password": "solo admin permanent password"},
    )
    admin_id = created["user"]["id"]

    demote = client.put(
        f"/workspaces/{workspace.id}/memberships/{admin_id}",
        headers=_csrf_headers(client),
        json={"role": "viewer"},
    )
    remove = client.delete(
        f"/workspaces/{workspace.id}/memberships/{admin_id}",
        headers=_csrf_headers(client),
    )

    assert demote.status_code == 409
    assert demote.json()["detail"]["code"] == "last_active_workspace_admin"
    assert remove.status_code == 409
    assert remove.json()["detail"]["code"] == "last_active_workspace_admin"
    membership = WorkspaceMembershipRepository(session).get_membership(
        workspace_id=workspace.id,
        user_id=UUID(admin_id),
    )
    assert membership is not None and membership.role == "admin"
