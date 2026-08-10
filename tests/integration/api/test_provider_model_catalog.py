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
    User,
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
            # User must exist: bootstrap auth fails closed when the table is missing.
            User.__table__,
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
    # Model listing rarely returns list prices; post-sync fill applies Alibaba catalog.
    embedding_pricing = list_response.json()["items"][0]["pricing"]
    assert embedding_pricing is not None
    assert embedding_pricing["input_per_million_tokens_usd"] == 0.07
    assert embedding_pricing.get("source") == "alibaba_model_studio_singapore_list"
    synced_ids = {item["model_id"] for item in sync_response.json()["items"]}
    # Provider /models often omits service models; seed declared-capability defaults.
    assert "qwen3-rerank" in synced_ids
    assert "text-embedding-v4" in synced_ids
    chat_row = next(
        item
        for item in sync_response.json()["items"]
        if item["model_id"] == "qwen-plus"
    )
    assert chat_row["pricing"] is not None
    assert chat_row["pricing"]["input_per_million_tokens_usd"] == 0.4
    assert chat_row["pricing"]["output_per_million_tokens_usd"] == 1.2
    rerank_row = next(
        item
        for item in sync_response.json()["items"]
        if item["model_id"] == "qwen3-rerank"
    )
    assert rerank_row["capabilities"] == ["rerank"]
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
        # Modern inference treats unknown Qwen text ids as chat (Model Studio).
        "qwen-experimental-preview": ["chat"],
    }
    assert [item["model_id"] for item in chat_models_response.json()["items"]] == [
        "qwen-experimental-preview",
        "qwen-plus",
    ]


def test_provider_connection_capability_edit_prunes_stale_service_seeds(
    monkeypatch,
) -> None:
    """Narrowing Token Plan to chat-only must drop seeded rerank/embed rows."""

    key = base64.urlsafe_b64encode(b"9" * 32).decode("ascii")
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
            "capabilities": [
                "chat",
                "dense_embedding",
                "sparse_embedding",
                "rerank",
            ],
            "api_key": "sk-hosted-secret",
        },
    )
    sync_full = client.post("/runtime-settings/connections/qwen-hosted/models/sync")
    assert sync_full.status_code == 200
    full_ids = {item["model_id"] for item in sync_full.json()["items"]}
    assert "qwen3-rerank" in full_ids
    assert "text-embedding-v4" in full_ids

    narrow = client.put(
        "/runtime-settings/connections/qwen-hosted",
        json={
            "provider": "qwen",
            "connection_type": "hosted",
            "base_url": "https://dashscope.example.test/compatible-mode/v1",
            "capabilities": ["chat", "contextualization", "vision"],
        },
    )
    assert narrow.status_code == 200

    listed = client.get(
        "/runtime-settings/models",
        params={"connection_id": "qwen-hosted"},
    )
    assert listed.status_code == 200
    remaining = {item["model_id"] for item in listed.json()["items"]}
    assert "qwen3-rerank" not in remaining
    assert "text-embedding-v4" not in remaining
    assert "qwen-plus" in remaining
