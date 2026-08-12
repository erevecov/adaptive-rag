"""HTTP surface for durable user memory (Bloque C minima)."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import get_session
from adaptive_rag.api.routes.chat import _with_approved_user_memory
from adaptive_rag.auth import hash_access_token
from adaptive_rag.chat import ChatRequest
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    User,
    UserAccessToken,
    UserMemory,
    Workspace,
    WorkspaceMembership,
)
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
            UserMemory.__table__,
        ],
    )
    return create_session_factory(engine)()


def _client(*, session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _create_user(
    session: Session,
    *,
    email: str,
    token: str,
    system_role: str = "user",
) -> User:
    repo = UserRepository(session)
    user = repo.create_user(email=email, display_name=email, system_role=system_role)
    repo.upsert_access_token(
        user_id=user.id,
        token_hash=hash_access_token(token),
        label=f"{email} token",
    )
    return user


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_propose_list_approve_and_chat_injection_path() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="Mem API")
    user = _create_user(session, email="mem@example.com", token="mem-token")
    WorkspaceMembershipRepository(session).upsert_membership(
        workspace_id=workspace.id,
        user_id=user.id,
        role="contributor",
    )
    session.commit()
    client = _client(session=session)

    unauth = client.post(
        "/users/me/memories",
        json={"content": "no auth"},
    )
    assert unauth.status_code == 401

    proposed = client.post(
        "/users/me/memories",
        headers=_bearer("mem-token"),
        json={
            "content": "  Prefer concise answers  ",
            "workspace_id": str(workspace.id),
        },
    )
    assert proposed.status_code == 201, proposed.text
    body = proposed.json()
    assert body["status"] == "proposed"
    assert body["content"] == "Prefer concise answers"
    assert body["workspace_id"] == str(workspace.id)
    memory_id = body["id"]

    listed = client.get("/users/me/memories", headers=_bearer("mem-token"))
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == memory_id

    # Chat inject must not include proposed memories
    request = ChatRequest(
        workspace_id=workspace.id,
        message="Hello",
        user_id=user.id,
    )
    not_injected = _with_approved_user_memory(
        session, request=request, user_id=user.id, workspace_id=workspace.id
    )
    assert not_injected.message == "Hello"
    assert not_injected.user_memory is None

    approved = client.post(
        f"/users/me/memories/{memory_id}/approve",
        headers=_bearer("mem-token"),
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    injected = _with_approved_user_memory(
        session, request=request, user_id=user.id, workspace_id=workspace.id
    )
    # Raw user turn must stay untouched for audit/history/condenser.
    assert injected.message == "Hello"
    assert injected.user_memory is not None
    assert "User memory (approved):" in injected.user_memory
    assert "Prefer concise answers" in injected.user_memory


def test_reject_and_restore_via_approve_api() -> None:
    session = _make_session()
    _create_user(session, email="rej@example.com", token="rej-token")
    session.commit()
    client = _client(session=session)

    created = client.post(
        "/users/me/memories",
        headers=_bearer("rej-token"),
        json={"content": "Timezone is UTC"},
    )
    assert created.status_code == 201
    memory_id = created.json()["id"]

    rejected = client.post(
        f"/users/me/memories/{memory_id}/reject",
        headers=_bearer("rej-token"),
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    restored = client.post(
        f"/users/me/memories/{memory_id}/approve",
        headers=_bearer("rej-token"),
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "approved"

    conflict = client.post(
        f"/users/me/memories/{memory_id}/approve",
        headers=_bearer("rej-token"),
    )
    assert conflict.status_code == 409


def test_foreign_memory_hidden_and_not_approvable() -> None:
    session = _make_session()
    _create_user(session, email="owner@example.com", token="owner-token")
    _create_user(session, email="other@example.com", token="other-token")
    session.commit()
    client = _client(session=session)

    created = client.post(
        "/users/me/memories",
        headers=_bearer("owner-token"),
        json={"content": "Owner only memory"},
    )
    assert created.status_code == 201
    memory_id = created.json()["id"]

    other_list = client.get("/users/me/memories", headers=_bearer("other-token"))
    assert other_list.status_code == 200
    assert other_list.json()["items"] == []

    foreign_approve = client.post(
        f"/users/me/memories/{memory_id}/approve",
        headers=_bearer("other-token"),
    )
    assert foreign_approve.status_code == 404

    missing = client.post(
        f"/users/me/memories/{uuid4()}/approve",
        headers=_bearer("owner-token"),
    )
    assert missing.status_code == 404


def test_empty_content_validation() -> None:
    session = _make_session()
    _create_user(session, email="empty@example.com", token="empty-token")
    session.commit()
    client = _client(session=session)

    # Pydantic min_length=1 rejects empty string before service
    response = client.post(
        "/users/me/memories",
        headers=_bearer("empty-token"),
        json={"content": ""},
    )
    assert response.status_code == 422

    # Whitespace-only reaches service strip check
    whitespace = client.post(
        "/users/me/memories",
        headers=_bearer("empty-token"),
        json={"content": "   "},
    )
    assert whitespace.status_code == 422


def test_propose_workspace_scoped_without_membership_forbidden() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="Secret Workspace")
    _create_user(session, email="outsider@example.com", token="out-token")
    session.commit()
    client = _client(session=session)

    denied = client.post(
        "/users/me/memories",
        headers=_bearer("out-token"),
        json={
            "content": "Inject into foreign workspace",
            "workspace_id": str(workspace.id),
        },
    )
    assert denied.status_code == 403
    assert denied.json()["detail"] == "workspace access required"

    listed = client.get("/users/me/memories", headers=_bearer("out-token"))
    assert listed.status_code == 200
    assert listed.json()["items"] == []


def test_approve_workspace_scoped_without_membership_forbidden() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="Revoked Access")
    user = _create_user(session, email="member@example.com", token="mem-token")
    memberships = WorkspaceMembershipRepository(session)
    memberships.upsert_membership(
        workspace_id=workspace.id,
        user_id=user.id,
        role="contributor",
    )
    session.commit()
    client = _client(session=session)

    proposed = client.post(
        "/users/me/memories",
        headers=_bearer("mem-token"),
        json={"content": "Workspace preference", "workspace_id": str(workspace.id)},
    )
    assert proposed.status_code == 201, proposed.text
    memory_id = proposed.json()["id"]

    assert memberships.remove_membership(workspace_id=workspace.id, user_id=user.id)
    session.commit()

    denied = client.post(
        f"/users/me/memories/{memory_id}/approve",
        headers=_bearer("mem-token"),
    )
    assert denied.status_code == 403
    assert denied.json()["detail"] == "workspace access required"

    request = ChatRequest(
        workspace_id=workspace.id,
        message="Hello",
        user_id=user.id,
    )
    not_injected = _with_approved_user_memory(
        session, request=request, user_id=user.id, workspace_id=workspace.id
    )
    assert not_injected.user_memory is None


def test_superadmin_can_propose_workspace_scoped_without_membership() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="Any Workspace")
    _create_user(
        session,
        email="admin@example.com",
        token="admin-token",
        system_role="superadmin",
    )
    session.commit()
    client = _client(session=session)

    proposed = client.post(
        "/users/me/memories",
        headers=_bearer("admin-token"),
        json={"content": "Admin note", "workspace_id": str(workspace.id)},
    )
    assert proposed.status_code == 201, proposed.text
    memory_id = proposed.json()["id"]

    approved = client.post(
        f"/users/me/memories/{memory_id}/approve",
        headers=_bearer("admin-token"),
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


def test_patch_proposed_and_reject_approved_via_api() -> None:
    session = _make_session()
    user = _create_user(session, email="patch@example.com", token="patch-token")
    session.commit()
    client = _client(session=session)

    created = client.post(
        "/users/me/memories",
        headers=_bearer("patch-token"),
        json={"content": "Draft preference"},
    )
    assert created.status_code == 201
    memory_id = created.json()["id"]

    patched = client.patch(
        f"/users/me/memories/{memory_id}",
        headers=_bearer("patch-token"),
        json={"content": "  Edited preference  "},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["content"] == "Edited preference"
    assert patched.json()["status"] == "proposed"

    approved = client.post(
        f"/users/me/memories/{memory_id}/approve",
        headers=_bearer("patch-token"),
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    conflict = client.patch(
        f"/users/me/memories/{memory_id}",
        headers=_bearer("patch-token"),
        json={"content": "Should fail"},
    )
    assert conflict.status_code == 409

    request = ChatRequest(
        workspace_id=uuid4(),
        message="Hello",
        user_id=user.id,
    )
    injected = _with_approved_user_memory(
        session, request=request, user_id=user.id, workspace_id=None
    )
    assert injected.user_memory is not None
    assert "Edited preference" in injected.user_memory

    removed = client.post(
        f"/users/me/memories/{memory_id}/reject",
        headers=_bearer("patch-token"),
    )
    assert removed.status_code == 200
    assert removed.json()["status"] == "rejected"

    cleared = _with_approved_user_memory(
        session, request=request, user_id=user.id, workspace_id=None
    )
    assert cleared.user_memory is None

    restored = client.post(
        f"/users/me/memories/{memory_id}/approve",
        headers=_bearer("patch-token"),
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["status"] == "approved"

    reinjected = _with_approved_user_memory(
        session, request=request, user_id=user.id, workspace_id=None
    )
    assert reinjected.user_memory is not None
    assert "Edited preference" in reinjected.user_memory


def test_list_filter_by_status_and_invalid_status() -> None:
    session = _make_session()
    _create_user(session, email="filter@example.com", token="filter-token")
    session.commit()
    client = _client(session=session)

    first = client.post(
        "/users/me/memories",
        headers=_bearer("filter-token"),
        json={"content": "First preference"},
    )
    assert first.status_code == 201
    second = client.post(
        "/users/me/memories",
        headers=_bearer("filter-token"),
        json={"content": "Second preference"},
    )
    assert second.status_code == 201
    approved = client.post(
        f"/users/me/memories/{first.json()['id']}/approve",
        headers=_bearer("filter-token"),
    )
    assert approved.status_code == 200

    only_approved = client.get(
        "/users/me/memories?status=approved",
        headers=_bearer("filter-token"),
    )
    assert only_approved.status_code == 200
    approved_items = only_approved.json()["items"]
    assert [item["content"] for item in approved_items] == ["First preference"]

    only_proposed = client.get(
        "/users/me/memories?status=proposed",
        headers=_bearer("filter-token"),
    )
    assert only_proposed.status_code == 200
    proposed_items = only_proposed.json()["items"]
    assert [item["content"] for item in proposed_items] == ["Second preference"]

    invalid = client.get(
        "/users/me/memories?status=archived",
        headers=_bearer("filter-token"),
    )
    assert invalid.status_code == 422


def test_patch_rejected_memory_conflicts() -> None:
    session = _make_session()
    _create_user(session, email="patchrej@example.com", token="patchrej-token")
    session.commit()
    client = _client(session=session)

    created = client.post(
        "/users/me/memories",
        headers=_bearer("patchrej-token"),
        json={"content": "Draft to reject"},
    )
    assert created.status_code == 201
    memory_id = created.json()["id"]

    rejected = client.post(
        f"/users/me/memories/{memory_id}/reject",
        headers=_bearer("patchrej-token"),
    )
    assert rejected.status_code == 200

    conflict = client.patch(
        f"/users/me/memories/{memory_id}",
        headers=_bearer("patchrej-token"),
        json={"content": "Too late"},
    )
    assert conflict.status_code == 409


def test_foreign_memory_patch_and_reject_hidden() -> None:
    session = _make_session()
    _create_user(session, email="idor-owner@example.com", token="idor-owner-token")
    _create_user(session, email="idor-other@example.com", token="idor-other-token")
    session.commit()
    client = _client(session=session)

    created = client.post(
        "/users/me/memories",
        headers=_bearer("idor-owner-token"),
        json={"content": "Owner draft"},
    )
    assert created.status_code == 201
    memory_id = created.json()["id"]

    foreign_patch = client.patch(
        f"/users/me/memories/{memory_id}",
        headers=_bearer("idor-other-token"),
        json={"content": "Hijacked"},
    )
    assert foreign_patch.status_code == 404

    foreign_reject = client.post(
        f"/users/me/memories/{memory_id}/reject",
        headers=_bearer("idor-other-token"),
    )
    assert foreign_reject.status_code == 404

    owner_view = client.get(
        "/users/me/memories",
        headers=_bearer("idor-owner-token"),
    )
    assert owner_view.status_code == 200
    items = owner_view.json()["items"]
    assert len(items) == 1
    assert items[0]["content"] == "Owner draft"
    assert items[0]["status"] == "proposed"


def test_content_length_boundary() -> None:
    session = _make_session()
    _create_user(session, email="length@example.com", token="length-token")
    session.commit()
    client = _client(session=session)

    at_limit = client.post(
        "/users/me/memories",
        headers=_bearer("length-token"),
        json={"content": "x" * 4000},
    )
    assert at_limit.status_code == 201

    over_limit = client.post(
        "/users/me/memories",
        headers=_bearer("length-token"),
        json={"content": "x" * 4001},
    )
    assert over_limit.status_code == 422
