"""Tests for project-scoped runtime settings HTTP APIs."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import get_session
from adaptive_rag.auth import hash_access_token
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    GlobalChatModel,
    GlobalChatRetrievalSettings,
    Project,
    ProjectChatModel,
    ProjectChatRetrievalSettings,
    ProjectMembership,
    ProjectRuntimeSlotOverride,
    ProviderConnection,
    ProviderSecret,
    RuntimeSlotDefault,
    User,
)
from adaptive_rag.db.models.user import UserAccessToken
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
            ProviderConnection.__table__,
            ProviderSecret.__table__,
            RuntimeSlotDefault.__table__,
            GlobalChatModel.__table__,
            GlobalChatRetrievalSettings.__table__,
            ProjectRuntimeSlotOverride.__table__,
            ProjectChatModel.__table__,
            ProjectChatRetrievalSettings.__table__,
            User.__table__,
            UserAccessToken.__table__,
            ProjectMembership.__table__,
        ],
    )
    return create_session_factory(engine)()


def _client(*, session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _put_connection(
    client: TestClient,
    *,
    connection_id: str,
    provider: str = "qwen",
    connection_type: str = "hosted",
    capabilities: list[str],
) -> None:
    response = client.put(
        f"/runtime-settings/connections/{connection_id}",
        json={
            "provider": provider,
            "connection_type": connection_type,
            "capabilities": capabilities,
        },
    )
    assert response.status_code == 200


def _bearer(raw_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {raw_token}"}


def _create_user(
    session: Session,
    *,
    login: str,
    token: str,
) -> User:
    repo = UserRepository(session)
    user = repo.create_user(login=login, display_name=login, system_role="user")
    repo.upsert_access_token(
        user_id=user.id,
        token_hash=hash_access_token(token),
        label=f"{login} token",
    )
    return user


def _grant_project_role(
    session: Session,
    *,
    project: Project,
    user: User,
    role: str,
) -> None:
    ProjectMembershipRepository(session).upsert_membership(
        project_id=project.id,
        user_id=user.id,
        role=role,
    )


def test_project_runtime_settings_override_requires_project_admin() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    session.add(
        ProviderConnection(
            connection_id="qwen-hosted",
            provider="qwen",
            connection_type="hosted",
            base_url=None,
            capabilities_json=["rerank"],
            metadata_json=None,
        )
    )
    viewer = _create_user(session, login="viewer@example.com", token="viewer-token")
    admin = _create_user(session, login="admin@example.com", token="admin-token")
    _grant_project_role(session, project=project, user=viewer, role="viewer")
    _grant_project_role(session, project=project, user=admin, role="admin")
    session.commit()
    client = _client(session=session)

    denied = client.put(
        f"/projects/{project.id}/runtime-settings/slots/rerank",
        headers=_bearer("viewer-token"),
        json={"connection_id": "qwen-hosted", "model_id": "qwen3-rerank"},
    )
    allowed = client.put(
        f"/projects/{project.id}/runtime-settings/slots/rerank",
        headers=_bearer("admin-token"),
        json={"connection_id": "qwen-hosted", "model_id": "qwen3-rerank"},
    )

    assert denied.status_code == 403
    assert denied.json()["detail"] == "project admin role required"
    assert allowed.status_code == 200


def test_project_runtime_settings_api_overrides_and_resets_slot() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    session.commit()
    client = _client(session=session)
    _put_connection(client, connection_id="qwen-hosted", capabilities=["rerank"])
    _put_connection(
        client,
        connection_id="local-rerank",
        provider="local_openai_compatible",
        connection_type="local",
        capabilities=["rerank"],
    )
    client.put(
        "/runtime-settings/slots/rerank",
        json={"connection_id": "qwen-hosted", "model_id": "qwen3-rerank"},
    )

    override = client.put(
        f"/projects/{project.id}/runtime-settings/slots/rerank",
        json={
            "connection_id": "local-rerank",
            "model_id": "local-reranker",
            "parameters": {"top_n": 4},
        },
    )

    assert override.status_code == 200
    assert override.json()["source"] == "overridden"

    effective = client.get(f"/projects/{project.id}/runtime-settings")

    assert effective.status_code == 200
    assert effective.json()["slots"] == [
        {
            "slot": "rerank",
            "source": "overridden",
            "connection_id": "local-rerank",
            "model_id": "local-reranker",
            "parameters": {"top_n": 4},
        }
    ]

    reset = client.delete(f"/projects/{project.id}/runtime-settings/slots/rerank")
    inherited = client.get(f"/projects/{project.id}/runtime-settings")

    assert reset.status_code == 200
    assert reset.json() == {"deleted": True}
    assert inherited.json()["slots"][0]["source"] == "inherited"
    assert inherited.json()["slots"][0]["connection_id"] == "qwen-hosted"


def test_project_chat_retrieval_settings_api_overrides_and_resets() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    session.commit()
    client = _client(session=session)
    client.put(
        "/runtime-settings/chat/retrieval",
        json={
            "retrieval_limit": 6,
            "rerank_enabled": True,
            "rerank_candidate_limit": 11,
        },
    )

    inherited = client.get(f"/projects/{project.id}/runtime-settings")
    override = client.put(
        f"/projects/{project.id}/runtime-settings/chat/retrieval",
        json={
            "retrieval_limit": 4,
            "rerank_enabled": False,
            "rerank_candidate_limit": 8,
        },
    )
    effective = client.get(f"/projects/{project.id}/runtime-settings")
    reset = client.delete(f"/projects/{project.id}/runtime-settings/chat/retrieval")
    inherited_again = client.get(f"/projects/{project.id}/runtime-settings")

    assert inherited.status_code == 200
    assert inherited.json()["chat_retrieval"] == {
        "source": "global",
        "retrieval_limit": 6,
        "rerank_enabled": True,
        "rerank_candidate_limit": 11,
        "max_limit": 50,
    }
    assert override.status_code == 200
    assert override.json() == {
        "source": "project",
        "retrieval_limit": 4,
        "rerank_enabled": False,
        "rerank_candidate_limit": 8,
        "max_limit": 50,
    }
    assert effective.json()["chat_retrieval"]["source"] == "project"
    assert effective.json()["chat_retrieval"]["retrieval_limit"] == 4
    assert reset.status_code == 200
    assert reset.json() == {"deleted": True}
    assert inherited_again.json()["chat_retrieval"]["source"] == "global"
    assert inherited_again.json()["chat_retrieval"]["retrieval_limit"] == 6


def test_project_chat_model_api_overrides_pool_and_rejects_default_delete() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    session.commit()
    client = _client(session=session)
    _put_connection(client, connection_id="qwen-hosted", capabilities=["chat"])
    _put_connection(
        client,
        connection_id="local-chat",
        provider="local_openai_compatible",
        connection_type="local",
        capabilities=["chat"],
    )
    client.post(
        "/runtime-settings/chat/models",
        json={"connection_id": "qwen-hosted", "model_id": "qwen-plus"},
    )

    inherited = client.get(f"/projects/{project.id}/runtime-settings")

    assert inherited.json()["chat_models"][0]["source"] == "inherited"

    first = client.put(
        f"/projects/{project.id}/runtime-settings/chat/models",
        json={"connection_id": "local-chat", "model_id": "llama3.1:8b"},
    )

    assert first.status_code == 200
    assert first.json()["is_default"] is True
    assert first.json()["source"] == "overridden"

    delete_default = client.delete(
        f"/projects/{project.id}/runtime-settings/chat/models/local-chat/llama3.1:8b"
    )

    assert delete_default.status_code == 409
    assert delete_default.json()["detail"]["code"] == "cannot_delete_last_chat_model"


def test_project_runtime_settings_api_returns_404_for_missing_project() -> None:
    client = _client(session=_make_session())

    response = client.get(f"/projects/{uuid4()}/runtime-settings")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "project_not_found"
