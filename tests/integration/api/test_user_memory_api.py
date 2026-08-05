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
    Project,
    ProjectMembership,
    User,
    UserAccessToken,
    UserMemory,
)
from adaptive_rag.db.repositories import (
    ProjectMembershipRepository,
    ProjectRepository,
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
            Project.__table__,
            User.__table__,
            UserAccessToken.__table__,
            ProjectMembership.__table__,
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


def _create_user(session: Session, *, login: str, token: str) -> User:
    repo = UserRepository(session)
    user = repo.create_user(login=login, display_name=login)
    repo.upsert_access_token(
        user_id=user.id,
        token_hash=hash_access_token(token),
        label=f"{login} token",
    )
    return user


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_propose_list_approve_and_chat_injection_path() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="Mem API")
    user = _create_user(session, login="mem@example.com", token="mem-token")
    ProjectMembershipRepository(session).upsert_membership(
        project_id=project.id,
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
        json={"content": "  Prefer concise answers  ", "project_id": str(project.id)},
    )
    assert proposed.status_code == 201, proposed.text
    body = proposed.json()
    assert body["status"] == "proposed"
    assert body["content"] == "Prefer concise answers"
    assert body["project_id"] == str(project.id)
    memory_id = body["id"]

    listed = client.get("/users/me/memories", headers=_bearer("mem-token"))
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == memory_id

    # Chat inject must not include proposed memories
    request = ChatRequest(
        project_id=project.id,
        message="Hello",
        user_id=user.id,
    )
    not_injected = _with_approved_user_memory(
        session, request=request, user_id=user.id, project_id=project.id
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
        session, request=request, user_id=user.id, project_id=project.id
    )
    # Raw user turn must stay untouched for audit/history/condenser.
    assert injected.message == "Hello"
    assert injected.user_memory is not None
    assert "User memory (approved):" in injected.user_memory
    assert "Prefer concise answers" in injected.user_memory


def test_reject_and_double_review_via_api() -> None:
    session = _make_session()
    _create_user(session, login="rej@example.com", token="rej-token")
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

    conflict = client.post(
        f"/users/me/memories/{memory_id}/approve",
        headers=_bearer("rej-token"),
    )
    assert conflict.status_code == 409


def test_foreign_memory_hidden_and_not_approvable() -> None:
    session = _make_session()
    _create_user(session, login="owner@example.com", token="owner-token")
    _create_user(session, login="other@example.com", token="other-token")
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
    _create_user(session, login="empty@example.com", token="empty-token")
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
