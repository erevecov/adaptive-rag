"""Tests for global runtime settings HTTP APIs."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import get_session
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    GlobalChatModel,
    ProviderConnection,
    ProviderSecret,
    RuntimeSlotDefault,
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
            ProviderConnection.__table__,
            ProviderSecret.__table__,
            RuntimeSlotDefault.__table__,
            GlobalChatModel.__table__,
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
