"""Tests de auth local y RBAC por proyecto para la API M37."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import get_session
from adaptive_rag.auth import hash_access_token
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Source, User, Workspace, WorkspaceMembership
from adaptive_rag.db.models.user import UserAccessToken
from adaptive_rag.db.repositories import (
    UserRepository,
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)
from adaptive_rag.db.session import create_session_factory


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
            WorkspaceMembership.__table__,
            Source.__table__,
        ],
    )
    return create_session_factory(engine)()


def _client(*, session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _bearer(raw_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {raw_token}"}


def _create_user(
    session: Session,
    *,
    login: str,
    token: str,
    system_role: str = "user",
) -> User:
    repo = UserRepository(session)
    user = repo.create_user(
        login=login,
        display_name=login,
        system_role=system_role,
    )
    repo.upsert_access_token(
        user_id=user.id,
        token_hash=hash_access_token(token),
        label=f"{login} token",
    )
    return user


def test_me_resolves_bearer_token_user() -> None:
    session = _make_session()
    user = _create_user(session, login="viewer@example.com", token="viewer-token")
    session.commit()
    client = _client(session=session)

    response = client.get("/auth/me", headers=_bearer("viewer-token"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(user.id)
    assert payload["login"] == "viewer@example.com"
    assert payload["system_role"] == "user"
    assert payload["last_workspace_id"] is None


def test_auth_required_when_users_exist() -> None:
    session = _make_session()
    _create_user(session, login="viewer@example.com", token="viewer-token")
    session.commit()
    client = _client(session=session)

    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "authentication required"


def test_bootstrap_can_create_first_superadmin() -> None:
    session = _make_session()
    client = _client(session=session)

    response = client.post(
        "/admin/users",
        json={
            "login": "root@example.com",
            "display_name": "Root",
            "system_role": "superadmin",
            "access_token": "root-token",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["login"] == "root@example.com"
    assert payload["system_role"] == "superadmin"
    root = UserRepository(session).get_by_login("root@example.com")
    assert root is not None
    assert (
        UserRepository(session).get_user_by_token_hash(hash_access_token("root-token"))
        == root
    )


def test_superadmin_creates_users_and_workspace_memberships() -> None:
    session = _make_session()
    root = _create_user(
        session,
        login="root@example.com",
        token="root-token",
        system_role="superadmin",
    )
    workspace = WorkspaceRepository(session).create(name="Demo")
    session.commit()
    client = _client(session=session)

    user_response = client.post(
        "/admin/users",
        headers=_bearer("root-token"),
        json={
            "login": "admin@example.com",
            "display_name": "Admin",
            "system_role": "user",
            "access_token": "admin-token",
        },
    )
    admin_id = UUID(user_response.json()["id"])
    membership_response = client.put(
        f"/workspaces/{workspace.id}/memberships/{admin_id}",
        headers=_bearer("root-token"),
        json={"role": "admin"},
    )

    assert root.system_role == "superadmin"
    assert user_response.status_code == 200
    assert membership_response.status_code == 200
    assert membership_response.json()["role"] == "admin"
    assert (
        WorkspaceMembershipRepository(session).get_membership(
            workspace_id=workspace.id,
            user_id=admin_id,
        )
        is not None
    )


def test_workspace_admin_can_manage_workspace_users_but_viewer_cannot() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="Demo")
    admin = _create_user(session, login="admin@example.com", token="admin-token")
    viewer = _create_user(session, login="viewer@example.com", token="viewer-token")
    WorkspaceMembershipRepository(session).upsert_membership(
        workspace_id=workspace.id,
        user_id=admin.id,
        role="admin",
    )
    WorkspaceMembershipRepository(session).upsert_membership(
        workspace_id=workspace.id,
        user_id=viewer.id,
        role="viewer",
    )
    session.commit()
    client = _client(session=session)

    allowed = client.put(
        f"/workspaces/{workspace.id}/memberships/{viewer.id}",
        headers=_bearer("admin-token"),
        json={"role": "contributor"},
    )
    denied = client.put(
        f"/workspaces/{workspace.id}/memberships/{admin.id}",
        headers=_bearer("viewer-token"),
        json={"role": "viewer"},
    )

    assert allowed.status_code == 200
    assert allowed.json()["role"] == "contributor"
    assert denied.status_code == 403
    assert denied.json()["detail"] == "workspace admin role required"


def test_workspace_list_returns_only_membership_workspaces_for_non_superadmin() -> None:
    session = _make_session()
    allowed_workspace = WorkspaceRepository(session).create(name="Allowed")
    denied_workspace = WorkspaceRepository(session).create(name="Denied")
    viewer = _create_user(session, login="viewer@example.com", token="viewer-token")
    WorkspaceMembershipRepository(session).upsert_membership(
        workspace_id=allowed_workspace.id,
        user_id=viewer.id,
        role="viewer",
    )
    session.commit()
    client = _client(session=session)

    list_response = client.get("/workspaces", headers=_bearer("viewer-token"))
    denied_detail = client.get(
        f"/workspaces/{denied_workspace.id}",
        headers=_bearer("viewer-token"),
    )

    assert list_response.status_code == 200
    workspaces = {item["name"]: item for item in list_response.json()["items"]}
    # Membership-only listing: no existence disclosure of foreign workspaces.
    assert set(workspaces) == {"Allowed"}
    assert workspaces["Allowed"]["can_access"] is True
    assert workspaces["Allowed"]["access_role"] == "viewer"
    assert denied_detail.status_code == 403
    assert denied_detail.json()["detail"] == "workspace access required"


def test_superadmin_workspace_list_includes_all_workspaces() -> None:
    session = _make_session()
    WorkspaceRepository(session).create(name="Alpha")
    WorkspaceRepository(session).create(name="Beta")
    _create_user(
        session,
        login="root@example.com",
        token="root-token",
        system_role="superadmin",
    )
    session.commit()
    client = _client(session=session)

    list_response = client.get("/workspaces", headers=_bearer("root-token"))

    assert list_response.status_code == 200
    workspaces = {item["name"]: item for item in list_response.json()["items"]}
    assert set(workspaces) == {"Alpha", "Beta"}
    assert all(item["can_access"] is True for item in workspaces.values())
    assert all(item["access_role"] == "superadmin" for item in workspaces.values())


def test_user_can_store_accessible_last_workspace_preference() -> None:
    session = _make_session()
    allowed_workspace = WorkspaceRepository(session).create(name="Allowed")
    denied_workspace = WorkspaceRepository(session).create(name="Denied")
    viewer = _create_user(session, login="viewer@example.com", token="viewer-token")
    WorkspaceMembershipRepository(session).upsert_membership(
        workspace_id=allowed_workspace.id,
        user_id=viewer.id,
        role="viewer",
    )
    session.commit()
    client = _client(session=session)

    allowed = client.patch(
        "/auth/me/preferences",
        headers=_bearer("viewer-token"),
        json={"last_workspace_id": str(allowed_workspace.id)},
    )
    me = client.get("/auth/me", headers=_bearer("viewer-token"))
    denied = client.patch(
        "/auth/me/preferences",
        headers=_bearer("viewer-token"),
        json={"last_workspace_id": str(denied_workspace.id)},
    )
    cleared = client.patch(
        "/auth/me/preferences",
        headers=_bearer("viewer-token"),
        json={"last_workspace_id": None},
    )

    assert allowed.status_code == 200
    assert allowed.json()["last_workspace_id"] == str(allowed_workspace.id)
    assert me.json()["last_workspace_id"] == str(allowed_workspace.id)
    assert denied.status_code == 403
    assert denied.json()["detail"] == "workspace access required"
    assert cleared.status_code == 200
    assert cleared.json()["last_workspace_id"] is None
    session.refresh(viewer)
    assert viewer.last_workspace_id is None


def test_source_create_requires_contributor_or_workspace_admin() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="Demo")
    viewer = _create_user(session, login="viewer@example.com", token="viewer-token")
    contributor = _create_user(
        session,
        login="contributor@example.com",
        token="contributor-token",
    )
    WorkspaceMembershipRepository(session).upsert_membership(
        workspace_id=workspace.id,
        user_id=viewer.id,
        role="viewer",
    )
    WorkspaceMembershipRepository(session).upsert_membership(
        workspace_id=workspace.id,
        user_id=contributor.id,
        role="contributor",
    )
    session.commit()
    client = _client(session=session)

    denied = client.post(
        f"/workspaces/{workspace.id}/sources",
        headers=_bearer("viewer-token"),
        json={
            "source_type": "markdown",
            "external_id": "viewer.md",
            "extra_metadata": {"content": "viewer content"},
        },
    )
    allowed = client.post(
        f"/workspaces/{workspace.id}/sources",
        headers=_bearer("contributor-token"),
        json={
            "source_type": "markdown",
            "external_id": "contributor.md",
            "extra_metadata": {"content": "contributor content"},
        },
    )

    assert denied.status_code == 403
    assert denied.json()["detail"] == "workspace contributor role required"
    assert allowed.status_code == 200
    assert allowed.json()["external_id"] == "contributor.md"


def test_missing_workspace_membership_returns_403_for_workspace_tools() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="Demo")
    outsider = _create_user(session, login="outsider@example.com", token="token")
    session.commit()
    client = _client(session=session)

    response = client.get(
        f"/workspaces/{workspace.id}/sources",
        headers=_bearer("token"),
    )

    assert outsider.system_role == "user"
    assert response.status_code == 403
    assert response.json()["detail"] == "workspace access required"


def test_invalid_bearer_token_returns_401() -> None:
    session = _make_session()
    _create_user(session, login="viewer@example.com", token="viewer-token")
    session.commit()
    client = _client(session=session)

    response = client.get("/auth/me", headers=_bearer("wrong-token"))

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid access token"


def test_inactive_user_token_returns_inactive_user_error() -> None:
    session = _make_session()
    user = _create_user(session, login="viewer@example.com", token="viewer-token")
    user.is_active = False
    session.commit()
    client = _client(session=session)

    response = client.get("/auth/me", headers=_bearer("viewer-token"))

    assert response.status_code == 401
    assert response.json()["detail"] == "inactive_user"


def test_workspace_detail_returns_404_before_access_check_for_missing_workspace() -> (
    None
):
    session = _make_session()
    _create_user(session, login="viewer@example.com", token="viewer-token")
    session.commit()
    client = _client(session=session)

    response = client.get(f"/workspaces/{uuid4()}", headers=_bearer("viewer-token"))

    assert response.status_code == 404
    assert response.json()["detail"] == "workspace not found"
