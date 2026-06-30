"""Tests for provider model catalog HTTP APIs."""

from __future__ import annotations

import base64
from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import get_provider_model_lister, get_session
from adaptive_rag.config.settings import get_settings
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    GlobalChatModel,
    ProviderConnection,
    ProviderModelCatalog,
    ProviderSecret,
    RuntimeSlotDefault,
)
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
            ProviderModelInfo(
                model_id="qwen-plus",
                capabilities=("chat",),
                metadata={"object": "model", "owned_by": "system"},
            ),
            ProviderModelInfo(
                model_id="text-embedding-v4",
                capabilities=("dense_embedding", "sparse_embedding"),
                metadata={"name": "Qwen3 Embedding"},
                pricing={"input_per_million_tokens_usd": 0.07},
            ),
            ProviderModelInfo(
                model_id="qwen3-rerank",
                capabilities=("rerank",),
                metadata={"name": "Qwen Rerank"},
            ),
        ]


class UnclassifiedProviderModelLister:
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
            ProviderModelInfo(model_id="qwen-experimental-preview"),
        ]


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
            ProviderModelCatalog.__table__,
            RuntimeSlotDefault.__table__,
            GlobalChatModel.__table__,
        ],
    )
    return create_session_factory(engine)()


def _client(
    *,
    lister: StubProviderModelLister | UnclassifiedProviderModelLister,
    session: Session,
) -> TestClient:
    get_settings.cache_clear()
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_provider_model_lister] = lambda: lister
    return TestClient(app)


def test_provider_model_sync_persists_catalog_without_returning_secret(
    monkeypatch,
) -> None:
    key = base64.urlsafe_b64encode(b"3" * 32).decode("ascii")
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
            "capabilities": ["chat", "dense_embedding", "sparse_embedding", "rerank"],
        },
    )
    client.put(
        "/runtime-settings/connections/qwen-hosted/secrets/api_key",
        json={"value": "sk-hosted-secret"},
    )

    sync_response = client.post(
        "/runtime-settings/connections/qwen-hosted/models/sync"
    )
    list_response = client.get(
        "/runtime-settings/models",
        params={"connection_id": "qwen-hosted", "capability": "dense_embedding"},
    )

    assert sync_response.status_code == 200
    assert sync_response.json()["synced_count"] == 3
    assert "sk-hosted-secret" not in str(sync_response.json())
    assert lister.api_keys == ["sk-hosted-secret"]
    assert list_response.status_code == 200
    assert [
        item["model_id"] for item in list_response.json()["items"]
    ] == ["text-embedding-v4"]
    assert list_response.json()["items"][0]["pricing"] == {
        "input_per_million_tokens_usd": 0.07
    }
    chat_model = session.get(GlobalChatModel, ("qwen-hosted", "qwen-plus"))
    chat_default = session.get(RuntimeSlotDefault, "chat")
    dense_default = session.get(RuntimeSlotDefault, "dense_embedding")
    sparse_default = session.get(RuntimeSlotDefault, "sparse_embedding")
    rerank_default = session.get(RuntimeSlotDefault, "rerank")
    assert chat_model is not None
    assert chat_model.is_default is True
    assert chat_default is not None
    assert chat_default.model_id == "qwen-plus"
    assert dense_default is not None
    assert dense_default.model_id == "text-embedding-v4"
    assert sparse_default is None
    assert rerank_default is not None
    assert rerank_default.model_id == "qwen3-rerank"


def test_provider_model_sync_persists_unclassified_models_without_slot_capabilities(
    monkeypatch,
) -> None:
    key = base64.urlsafe_b64encode(b"7" * 32).decode("ascii")
    monkeypatch.setenv("ADAPTIVE_RAG_PROVIDER_SECRETS_KEY", key)
    session = _make_session()
    lister = UnclassifiedProviderModelLister()
    client = _client(lister=lister, session=session)
    client.put(
        "/runtime-settings/connections/qwen-hosted",
        json={
            "provider": "qwen",
            "connection_type": "hosted",
            "base_url": "https://dashscope.example.test/compatible-mode/v1",
            "capabilities": ["chat"],
            "api_key": "sk-hosted-secret",
        },
    )

    sync_response = client.post(
        "/runtime-settings/connections/qwen-hosted/models/sync"
    )
    chat_models_response = client.get(
        "/runtime-settings/models",
        params={"connection_id": "qwen-hosted", "capability": "chat"},
    )

    assert sync_response.status_code == 200
    payload = sync_response.json()
    assert payload["synced_count"] == 2
    assert {
        item["model_id"]: item["capabilities"] for item in payload["items"]
    } == {
        "qwen-plus": ["chat"],
        "qwen-experimental-preview": [],
    }
    assert [item["model_id"] for item in chat_models_response.json()["items"]] == [
        "qwen-plus"
    ]
