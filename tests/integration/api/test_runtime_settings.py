"""Tests for global runtime settings HTTP APIs."""

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
    GlobalChatModel,
    GlobalChatRetrievalSettings,
    ProviderConnection,
    ProviderSecret,
    RuntimeSlotDefault,
    User,
)
from adaptive_rag.db.models.user import UserAccessToken
from adaptive_rag.db.repositories import UserRepository
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
            ProviderConnection.__table__,
            ProviderSecret.__table__,
            RuntimeSlotDefault.__table__,
            GlobalChatModel.__table__,
            GlobalChatRetrievalSettings.__table__,
            User.__table__,
            UserAccessToken.__table__,
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
    base_url: str | None = None,
) -> None:
    response = client.put(
        f"/runtime-settings/connections/{connection_id}",
        json={
            "provider": provider,
            "connection_type": connection_type,
            "base_url": base_url,
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


def test_global_runtime_settings_require_superadmin_when_users_exist() -> None:
    session = _make_session()
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
    _create_user(session, login="viewer@example.com", token="viewer-token")
    _create_user(
        session,
        login="root@example.com",
        token="root-token",
        system_role="superadmin",
    )
    session.commit()
    client = _client(session=session)

    unauthenticated = client.get("/runtime-settings/slots")
    denied = client.put(
        "/runtime-settings/slots/rerank",
        headers=_bearer("viewer-token"),
        json={"connection_id": "qwen-hosted", "model_id": "qwen3-rerank"},
    )
    allowed = client.put(
        "/runtime-settings/slots/rerank",
        headers=_bearer("root-token"),
        json={"connection_id": "qwen-hosted", "model_id": "qwen3-rerank"},
    )

    assert unauthenticated.status_code == 401
    assert denied.status_code == 403
    assert denied.json()["detail"] == "superadmin role required"
    assert allowed.status_code == 200


def test_slot_defaults_api_upserts_lists_and_rejects_unknown_slots() -> None:
    session = _make_session()
    client = _client(session=session)
    _put_connection(client, connection_id="qwen-hosted", capabilities=["rerank"])

    response = client.put(
        "/runtime-settings/slots/rerank",
        json={
            "connection_id": "qwen-hosted",
            "model_id": "qwen3-rerank",
            "parameters": {"top_n": 8},
        },
    )

    assert response.status_code == 200
    assert response.json()["slot"] == "rerank"
    assert response.json()["parameters"] == {"top_n": 8}

    list_response = client.get("/runtime-settings/slots")

    assert list_response.status_code == 200
    assert [item["slot"] for item in list_response.json()["items"]] == ["rerank"]

    unsupported = client.put(
        "/runtime-settings/slots/voice",
        json={"connection_id": "qwen-hosted", "model_id": "qwen-voice"},
    )

    assert unsupported.status_code == 422
    assert unsupported.json()["detail"]["code"] == "unsupported_slot"


def test_chat_retrieval_settings_api_returns_defaults_and_updates_limits() -> None:
    session = _make_session()
    client = _client(session=session)

    defaults = client.get("/runtime-settings/chat/retrieval")
    update = client.put(
        "/runtime-settings/chat/retrieval",
        json={
            "retrieval_limit": 7,
            "rerank_enabled": True,
            "rerank_candidate_limit": 12,
        },
    )
    invalid = client.put(
        "/runtime-settings/chat/retrieval",
        json={
            "retrieval_limit": 51,
            "rerank_enabled": True,
            "rerank_candidate_limit": 51,
        },
    )

    assert defaults.status_code == 200
    assert defaults.json() == {
        "retrieval_limit": 5,
        "rerank_enabled": True,
        "rerank_candidate_limit": 10,
        "max_limit": 50,
    }
    assert update.status_code == 200
    assert update.json() == {
        "retrieval_limit": 7,
        "rerank_enabled": True,
        "rerank_candidate_limit": 12,
        "max_limit": 50,
    }
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "invalid_runtime_settings"


def test_chat_model_api_manages_pool_default_and_delete_invariants() -> None:
    session = _make_session()
    client = _client(session=session)
    _put_connection(client, connection_id="qwen-hosted", capabilities=["chat"])
    _put_connection(
        client,
        connection_id="local-chat",
        provider="local_openai_compatible",
        connection_type="local",
        base_url="http://localhost:11434/v1",
        capabilities=["chat"],
    )

    first = client.post(
        "/runtime-settings/chat/models",
        json={"connection_id": "qwen-hosted", "model_id": "qwen-plus"},
    )
    second = client.post(
        "/runtime-settings/chat/models",
        json={"connection_id": "local-chat", "model_id": "llama3.1:8b"},
    )

    assert first.status_code == 200
    assert first.json()["is_default"] is True
    assert second.status_code == 200
    assert second.json()["is_default"] is False

    default_response = client.put(
        "/runtime-settings/chat/models/local-chat/llama3.1:8b/default"
    )

    assert default_response.status_code == 200
    assert default_response.json()["is_default"] is True

    models_response = client.get("/runtime-settings/chat/models")

    assert models_response.status_code == 200
    assert [
        (item["connection_id"], item["model_id"], item["is_default"])
        for item in models_response.json()["items"]
    ] == [
        ("local-chat", "llama3.1:8b", True),
        ("qwen-hosted", "qwen-plus", False),
    ]

    delete_default = client.delete(
        "/runtime-settings/chat/models/local-chat/llama3.1:8b"
    )

    assert delete_default.status_code == 409
    assert delete_default.json()["detail"]["code"] == "cannot_delete_default_chat_model"
