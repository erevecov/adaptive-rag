"""Tests for global runtime provider connection HTTP API."""

from __future__ import annotations

import base64
from collections.abc import Iterator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import get_provider_model_lister, get_session
from adaptive_rag.auth import hash_access_token
from adaptive_rag.config.settings import get_settings
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import ProviderConnection, ProviderSecret, User
from adaptive_rag.db.models.user import UserAccessToken
from adaptive_rag.db.repositories import UserRepository
from adaptive_rag.db.session import create_session_factory
from adaptive_rag.provider_models import ProviderModelInfo


class StubProviderModelLister:
    def __init__(self) -> None:
        self.api_keys: list[str | None] = []

    def list_models(
        self,
        connection: ProviderConnection,
        *,
        api_key: str | None,
    ) -> list[ProviderModelInfo]:
        self.api_keys.append(api_key)
        return [
            ProviderModelInfo(model_id="qwen-plus", capabilities=("chat",)),
            ProviderModelInfo(
                model_id="text-embedding-v4",
                capabilities=("dense_embedding",),
            ),
        ]


class FailingProviderModelLister:
    def list_models(
        self,
        connection: ProviderConnection,
        *,
        api_key: str | None,
    ) -> list[ProviderModelInfo]:
        raise ValueError("provider model list failed with status 401")


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
            User.__table__,
            UserAccessToken.__table__,
        ],
    )
    return create_session_factory(engine)()


def _client(
    *,
    lister: FailingProviderModelLister | StubProviderModelLister | None = None,
    session: Session,
) -> TestClient:
    get_settings.cache_clear()
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    if lister is not None:
        app.dependency_overrides[get_provider_model_lister] = lambda: lister
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


def test_provider_connections_require_superadmin_when_users_exist() -> None:
    session = _make_session()
    _create_user(session, login="viewer@example.com", token="viewer-token")
    _create_user(
        session,
        login="root@example.com",
        token="root-token",
        system_role="superadmin",
    )
    session.commit()
    client = _client(session=session)

    unauthenticated = client.get("/runtime-settings/connections")
    denied = client.put(
        "/runtime-settings/connections/qwen-hosted",
        headers=_bearer("viewer-token"),
        json={
            "provider": "qwen",
            "connection_type": "hosted",
            "capabilities": ["chat"],
        },
    )
    allowed = client.put(
        "/runtime-settings/connections/qwen-hosted",
        headers=_bearer("root-token"),
        json={
            "provider": "qwen",
            "connection_type": "hosted",
            "capabilities": ["chat"],
        },
    )

    assert unauthenticated.status_code == 401
    assert denied.status_code == 403
    assert denied.json()["detail"] == "superadmin role required"
    assert allowed.status_code == 200


def test_connection_api_lists_hosted_and_local_without_secrets() -> None:
    session = _make_session()
    client = _client(session=session)

    hosted = client.put(
        "/runtime-settings/connections/qwen-hosted",
        json={
            "provider": "qwen",
            "connection_type": "hosted",
            "base_url": "https://dashscope.example.test/compatible-mode/v1",
            "capabilities": ["dense_embedding", "sparse_embedding", "rerank"],
            "metadata": {"label": "Qwen hosted"},
        },
    )
    local = client.put(
        "/runtime-settings/connections/local-chat",
        json={
            "provider": "local_openai_compatible",
            "connection_type": "local",
            "base_url": "http://localhost:11434/v1",
            "capabilities": ["chat"],
        },
    )

    assert hosted.status_code == 200
    assert local.status_code == 200

    response = client.get("/runtime-settings/connections")

    assert response.status_code == 200
    payload = response.json()
    assert [item["connection_id"] for item in payload["items"]] == [
        "local-chat",
        "qwen-hosted",
    ]
    assert payload["items"][0]["secrets"] == []
    assert "sk-hosted-secret" not in str(payload)


def test_connection_create_api_generates_connection_id() -> None:
    session = _make_session()
    client = _client(session=session)

    response = client.post(
        "/runtime-settings/connections",
        json={
            "provider": "qwen",
            "connection_type": "hosted",
            "base_url": "https://dashscope.example.test/compatible-mode/v1",
            "capabilities": ["chat", "dense_embedding"],
            "metadata": {"label": "Hosted Qwen"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["connection_id"].startswith("qwen-hosted-")
    assert payload["provider"] == "qwen"
    assert session.get(ProviderConnection, payload["connection_id"]) is not None


def test_connection_create_rejects_empty_capabilities() -> None:
    session = _make_session()
    client = _client(session=session)

    response = client.post(
        "/runtime-settings/connections",
        json={
            "provider": "qwen",
            "connection_type": "hosted",
            "capabilities": [],
        },
    )

    assert response.status_code == 422


def test_connection_create_persists_inline_api_key_without_readback(
    monkeypatch,
) -> None:
    key = base64.urlsafe_b64encode(b"4" * 32).decode("ascii")
    monkeypatch.setenv("ADAPTIVE_RAG_PROVIDER_SECRETS_KEY", key)
    session = _make_session()
    client = _client(session=session)

    response = client.post(
        "/runtime-settings/connections",
        json={
            "provider": "qwen",
            "connection_type": "hosted",
            "base_url": "https://dashscope.example.test/compatible-mode/v1",
            "capabilities": ["chat", "dense_embedding"],
            "api_key": "sk-inline-secret",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["secrets"][0]["configured"] is True
    assert payload["secrets"][0]["secret_name"] == "api_key"
    assert payload["secrets"][0]["last_four"] == "cret"
    assert "api_key" not in payload
    assert "sk-inline-secret" not in str(payload)

    row = session.get(ProviderSecret, (payload["connection_id"], "api_key"))

    assert row is not None
    assert b"sk-inline-secret" not in row.encrypted_value


def test_secret_api_persists_status_without_reading_value_back(monkeypatch) -> None:
    key = base64.urlsafe_b64encode(b"2" * 32).decode("ascii")
    monkeypatch.setenv("ADAPTIVE_RAG_PROVIDER_SECRETS_KEY", key)
    session = _make_session()
    client = _client(session=session)
    client.put(
        "/runtime-settings/connections/qwen-hosted",
        json={
            "provider": "qwen",
            "connection_type": "hosted",
            "capabilities": ["chat"],
        },
    )

    response = client.put(
        "/runtime-settings/connections/qwen-hosted/secrets/api_key",
        json={"value": "sk-hosted-secret"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is True
    assert payload["last_four"] == "cret"
    assert payload["fingerprint"] is not None
    assert "value" not in payload
    assert "encrypted_value" not in payload
    assert "sk-hosted-secret" not in str(payload)

    row = session.get(ProviderSecret, ("qwen-hosted", "api_key"))

    assert row is not None
    assert b"sk-hosted-secret" not in row.encrypted_value


def test_secret_write_bootstraps_local_encryption_key_file(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("ADAPTIVE_RAG_PROVIDER_SECRETS_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    session = _make_session()
    client = _client(session=session)
    client.put(
        "/runtime-settings/connections/qwen-hosted",
        json={
            "provider": "qwen",
            "connection_type": "hosted",
            "capabilities": ["chat"],
        },
    )

    response = client.put(
        "/runtime-settings/connections/qwen-hosted/secrets/api_key",
        json={"value": "sk-hosted-secret"},
    )

    assert response.status_code == 200
    assert (tmp_path / ".adaptive-rag" / "provider-secrets.key").exists()
    row = session.get(ProviderSecret, ("qwen-hosted", "api_key"))
    assert row is not None
    assert b"sk-hosted-secret" not in row.encrypted_value


def test_connection_check_lists_provider_models_without_persisting_catalog(
    monkeypatch,
) -> None:
    key = base64.urlsafe_b64encode(b"5" * 32).decode("ascii")
    monkeypatch.setenv("ADAPTIVE_RAG_PROVIDER_SECRETS_KEY", key)
    session = _make_session()
    lister = StubProviderModelLister()
    client = _client(lister=lister, session=session)
    client.put(
        "/runtime-settings/connections/qwen-hosted",
        json={
            "provider": "qwen",
            "connection_type": "hosted",
            "base_url": "https://dashscope.example.test/compatible-mode/v1",
            "capabilities": ["chat", "dense_embedding"],
            "api_key": "sk-hosted-secret",
        },
    )

    response = client.post("/runtime-settings/connections/qwen-hosted/check")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "connection_id": "qwen-hosted",
        "message": "provider model list succeeded",
        "model_count": 2,
        "ok": True,
    }
    assert lister.api_keys == ["sk-hosted-secret"]
    assert "sk-hosted-secret" not in str(payload)


def test_connection_check_reports_provider_failures_without_syncing(
    monkeypatch,
) -> None:
    key = base64.urlsafe_b64encode(b"6" * 32).decode("ascii")
    monkeypatch.setenv("ADAPTIVE_RAG_PROVIDER_SECRETS_KEY", key)
    session = _make_session()
    client = _client(lister=FailingProviderModelLister(), session=session)
    client.put(
        "/runtime-settings/connections/qwen-hosted",
        json={
            "provider": "qwen",
            "connection_type": "hosted",
            "base_url": "https://dashscope.example.test/compatible-mode/v1",
            "capabilities": ["chat", "dense_embedding"],
            "api_key": "sk-hosted-secret",
        },
    )

    response = client.post("/runtime-settings/connections/qwen-hosted/check")

    assert response.status_code == 200
    assert response.json() == {
        "connection_id": "qwen-hosted",
        "message": "provider model list failed with status 401",
        "model_count": 0,
        "ok": False,
    }
