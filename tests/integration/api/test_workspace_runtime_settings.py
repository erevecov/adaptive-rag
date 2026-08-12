"""Tests for workspace-scoped runtime settings HTTP APIs."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

from _legacy_auth_support import install_legacy_auth_override
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
    ProviderConnection,
    ProviderModelCatalog,
    ProviderSecret,
    RuntimeSlotDefault,
    User,
    Workspace,
    WorkspaceChatModel,
    WorkspaceChatRetrievalSettings,
    WorkspaceMembership,
    WorkspaceRuntimeSlotOverride,
)
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
            ProviderConnection.__table__,
            ProviderModelCatalog.__table__,
            ProviderSecret.__table__,
            RuntimeSlotDefault.__table__,
            GlobalChatModel.__table__,
            GlobalChatRetrievalSettings.__table__,
            WorkspaceRuntimeSlotOverride.__table__,
            WorkspaceChatModel.__table__,
            WorkspaceChatRetrievalSettings.__table__,
            User.__table__,
            UserAccessToken.__table__,
            WorkspaceMembership.__table__,
        ],
    )
    return create_session_factory(engine)()


def _client(*, session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    install_legacy_auth_override(app, session)
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
    email: str,
    token: str,
) -> User:
    repo = UserRepository(session)
    user = repo.create_user(email=email, display_name=email, system_role="user")
    repo.upsert_access_token(
        user_id=user.id,
        token_hash=hash_access_token(token),
        label=f"{email} token",
    )
    return user


def _grant_workspace_role(
    session: Session,
    *,
    workspace: Workspace,
    user: User,
    role: str,
) -> None:
    WorkspaceMembershipRepository(session).upsert_membership(
        workspace_id=workspace.id,
        user_id=user.id,
        role=role,
    )


def test_workspace_runtime_settings_override_requires_workspace_admin() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
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
    viewer = _create_user(session, email="viewer@example.com", token="viewer-token")
    admin = _create_user(session, email="admin@example.com", token="admin-token")
    _grant_workspace_role(session, workspace=workspace, user=viewer, role="viewer")
    _grant_workspace_role(session, workspace=workspace, user=admin, role="admin")
    session.commit()
    client = _client(session=session)

    denied = client.put(
        f"/workspaces/{workspace.id}/runtime-settings/slots/rerank",
        headers=_bearer("viewer-token"),
        json={"connection_id": "qwen-hosted", "model_id": "qwen3-rerank"},
    )
    allowed = client.put(
        f"/workspaces/{workspace.id}/runtime-settings/slots/rerank",
        headers=_bearer("admin-token"),
        json={"connection_id": "qwen-hosted", "model_id": "qwen3-rerank"},
    )

    assert denied.status_code == 403
    assert denied.json()["detail"] == "workspace admin role required"
    assert allowed.status_code == 200


def test_workspace_runtime_settings_api_overrides_and_resets_slot() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
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
        f"/workspaces/{workspace.id}/runtime-settings/slots/rerank",
        json={
            "connection_id": "local-rerank",
            "model_id": "local-reranker",
            "parameters": {"top_n": 4},
        },
    )

    assert override.status_code == 200
    assert override.json()["source"] == "overridden"

    effective = client.get(f"/workspaces/{workspace.id}/runtime-settings")

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

    reset = client.delete(f"/workspaces/{workspace.id}/runtime-settings/slots/rerank")
    inherited = client.get(f"/workspaces/{workspace.id}/runtime-settings")

    assert reset.status_code == 200
    assert reset.json() == {"deleted": True}
    assert inherited.json()["slots"][0]["source"] == "inherited"
    assert inherited.json()["slots"][0]["connection_id"] == "qwen-hosted"


def test_workspace_runtime_settings_api_accepts_vision_slot_override() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    session.commit()
    client = _client(session=session)
    _put_connection(
        client,
        connection_id="qwen-hosted",
        capabilities=["chat", "vision"],
    )

    override = client.put(
        f"/workspaces/{workspace.id}/runtime-settings/slots/vision",
        json={"connection_id": "qwen-hosted", "model_id": "qwen3-vl-plus"},
    )

    assert override.status_code == 200
    assert override.json()["source"] == "overridden"
    assert override.json()["slot"] == "vision"
    assert override.json()["model_id"] == "qwen3-vl-plus"


def test_workspace_chat_retrieval_settings_api_overrides_and_resets() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
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

    inherited = client.get(f"/workspaces/{workspace.id}/runtime-settings")
    override = client.put(
        f"/workspaces/{workspace.id}/runtime-settings/chat/retrieval",
        json={
            "retrieval_limit": 4,
            "rerank_enabled": False,
            "rerank_candidate_limit": 8,
        },
    )
    effective = client.get(f"/workspaces/{workspace.id}/runtime-settings")
    reset = client.delete(f"/workspaces/{workspace.id}/runtime-settings/chat/retrieval")
    inherited_again = client.get(f"/workspaces/{workspace.id}/runtime-settings")

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
        "source": "workspace",
        "retrieval_limit": 4,
        "rerank_enabled": False,
        "rerank_candidate_limit": 8,
        "max_limit": 50,
    }
    assert effective.json()["chat_retrieval"]["source"] == "workspace"
    assert effective.json()["chat_retrieval"]["retrieval_limit"] == 4
    assert reset.status_code == 200
    assert reset.json() == {"deleted": True}
    assert inherited_again.json()["chat_retrieval"]["source"] == "global"
    assert inherited_again.json()["chat_retrieval"]["retrieval_limit"] == 6


def test_workspace_chat_model_api_overrides_pool_and_rejects_default_delete() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
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

    inherited = client.get(f"/workspaces/{workspace.id}/runtime-settings")

    assert inherited.json()["chat_models"][0]["source"] == "inherited"

    first = client.put(
        f"/workspaces/{workspace.id}/runtime-settings/chat/models",
        json={"connection_id": "local-chat", "model_id": "llama3.1:8b"},
    )

    assert first.status_code == 200
    assert first.json()["is_default"] is True
    assert first.json()["source"] == "overridden"

    delete_default = client.delete(
        f"/workspaces/{workspace.id}/runtime-settings/chat/models/local-chat/llama3.1:8b"
    )

    assert delete_default.status_code == 409
    assert delete_default.json()["detail"]["code"] == "cannot_delete_last_chat_model"


def test_workspace_runtime_settings_api_returns_404_for_missing_workspace() -> None:
    client = _client(session=_make_session())

    response = client.get(f"/workspaces/{uuid4()}/runtime-settings")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "workspace_not_found"
