"""Role matrix for authoring lifecycle ops (M43)."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import get_session
from adaptive_rag.auth import hash_access_token
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Chunk,
    ChunkSparseEmbedding,
    Document,
    DocumentVersion,
    Project,
    ProjectMembership,
    Source,
    User,
    UserAccessToken,
)
from adaptive_rag.db.repositories import (
    ProjectMembershipRepository,
    ProjectRepository,
    SourceRepository,
    UserRepository,
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
            User.__table__,
            UserAccessToken.__table__,
            Project.__table__,
            ProjectMembership.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
            ChunkSparseEmbedding.__table__,
        ],
    )
    return create_session_factory(engine)()


def _seed(session: Session) -> dict[str, object]:
    users = UserRepository(session)
    superadmin = users.create_user(
        login="root",
        display_name="Root",
        system_role="superadmin",
    )
    admin = users.create_user(login="admin", display_name="Admin", system_role="user")
    contributor = users.create_user(
        login="contrib", display_name="Contrib", system_role="user"
    )
    viewer = users.create_user(
        login="viewer",
        display_name="Viewer",
        system_role="user",
    )
    for user, token in (
        (superadmin, "super-token"),
        (admin, "admin-token"),
        (contributor, "contrib-token"),
        (viewer, "viewer-token"),
    ):
        users.upsert_access_token(
            user_id=user.id,
            token_hash=hash_access_token(token),
            label=token,
        )
    project = ProjectRepository(session).create(name="Lifecycle")
    memberships = ProjectMembershipRepository(session)
    memberships.upsert_membership(
        project_id=project.id, user_id=admin.id, role="admin"
    )
    memberships.upsert_membership(
        project_id=project.id, user_id=contributor.id, role="contributor"
    )
    memberships.upsert_membership(
        project_id=project.id, user_id=viewer.id, role="viewer"
    )
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="notes.md",
        extra_metadata={"content": "# Notes"},
    )
    session.commit()
    return {
        "project": project,
        "source": source,
        "admin": admin,
        "viewer": viewer,
        "contributor": contributor,
    }


def _client(session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_role_matrix_update_delete_source_and_membership() -> None:
    session = _make_session()
    seeded = _seed(session)
    project = seeded["project"]
    source = seeded["source"]
    viewer_user = seeded["viewer"]
    client = _client(session)

    denied_patch = client.patch(
        f"/projects/{project.id}/sources/{source.id}",
        headers=_auth("viewer-token"),
        json={"tags": ["x"]},
    )
    allowed_patch = client.patch(
        f"/projects/{project.id}/sources/{source.id}",
        headers=_auth("contrib-token"),
        json={"tags": ["ok"]},
    )
    denied_delete = client.delete(
        f"/projects/{project.id}/sources/{source.id}",
        headers=_auth("viewer-token"),
    )
    denied_delete_contrib = client.delete(
        f"/projects/{project.id}/sources/{source.id}",
        headers=_auth("contrib-token"),
    )
    allowed_delete = client.delete(
        f"/projects/{project.id}/sources/{source.id}",
        headers=_auth("admin-token"),
    )

    assert denied_patch.status_code == 403
    assert allowed_patch.status_code == 200
    assert allowed_patch.json()["tags"] == ["ok"]
    assert denied_delete.status_code == 403
    assert denied_delete_contrib.status_code == 403
    assert allowed_delete.status_code == 200
    assert allowed_delete.json()["deleted_at"] is not None

    denied_membership = client.delete(
        f"/projects/{project.id}/memberships/{viewer_user.id}",
        headers=_auth("contrib-token"),
    )
    allowed_membership = client.delete(
        f"/projects/{project.id}/memberships/{viewer_user.id}",
        headers=_auth("admin-token"),
    )
    assert denied_membership.status_code == 403
    assert allowed_membership.status_code == 204


def test_soft_deleted_project_is_not_gettable_or_listed() -> None:
    """OpenSpec M43: after soft-delete, GET/list must omit the project."""

    session = _make_session()
    seeded = _seed(session)
    project = seeded["project"]
    client = _client(session)

    deleted = client.delete(
        f"/projects/{project.id}",
        headers=_auth("super-token"),
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted_at"] is not None

    # Access path used by all project-scoped routes (get_project_access).
    get_response = client.get(
        f"/projects/{project.id}",
        headers=_auth("admin-token"),
    )
    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "project not found"

    listed = client.get("/projects", headers=_auth("admin-token"))
    assert listed.status_code == 200
    assert all(item["id"] != str(project.id) for item in listed.json()["items"])

    # Contributor surface also 404s instead of operating on a tombstone.
    sources = client.get(
        f"/projects/{project.id}/sources",
        headers=_auth("contrib-token"),
    )
    assert sources.status_code == 404


def test_deactivate_user_and_revoke_token() -> None:
    session = _make_session()
    users = UserRepository(session)
    superadmin = users.create_user(
        login="root",
        display_name="Root",
        system_role="superadmin",
    )
    target = users.create_user(
        login="temp",
        display_name="Temp",
        system_role="user",
    )
    users.upsert_access_token(
        user_id=superadmin.id,
        token_hash=hash_access_token("super-token"),
    )
    users.upsert_access_token(
        user_id=target.id,
        token_hash=hash_access_token("temp-token"),
    )
    session.commit()
    client = _client(session)

    deactivated = client.post(
        f"/admin/users/{target.id}/deactivate",
        headers=_auth("super-token"),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    # Deactivated user token no longer authenticates.
    me = client.get("/auth/me", headers=_auth("temp-token"))
    assert me.status_code in {401, 403}

    users.upsert_access_token(
        user_id=target.id,
        token_hash=hash_access_token("temp-token-2"),
    )
    users.update_user(target.id, is_active=True)
    session.commit()
    revoked = client.post(
        "/admin/access-tokens/revoke",
        headers=_auth("super-token"),
        json={"access_token": "temp-token-2"},
    )
    assert revoked.status_code == 200
    assert revoked.json()["revoked"] is True
    me_after = client.get("/auth/me", headers=_auth("temp-token-2"))
    assert me_after.status_code in {401, 403}
