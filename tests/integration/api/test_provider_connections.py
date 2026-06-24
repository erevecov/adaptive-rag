"""Tests for global runtime provider connection HTTP API."""

from __future__ import annotations

import base64
from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import get_session
from adaptive_rag.config.settings import get_settings
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import ProviderConnection, ProviderSecret
from adaptive_rag.db.session import create_session_factory


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[ProviderConnection.__table__, ProviderSecret.__table__],
    )
    return create_session_factory(engine)()


def _client(*, session: Session) -> TestClient:
    get_settings.cache_clear()
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


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


def test_secret_write_requires_server_side_encryption_key(monkeypatch) -> None:
    monkeypatch.delenv("ADAPTIVE_RAG_PROVIDER_SECRETS_KEY", raising=False)
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

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "provider_secret_key_missing",
        "message": "ADAPTIVE_RAG_PROVIDER_SECRETS_KEY is required",
    }
    assert session.get(ProviderSecret, ("qwen-hosted", "api_key")) is None
