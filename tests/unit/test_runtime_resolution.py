"""Tests for effective runtime provider resolution."""

from __future__ import annotations

import base64

import pytest

from adaptive_rag.chat import QwenChatRunner
from adaptive_rag.chat.qwen import QwenHTTPChatClient
from adaptive_rag.config.settings import Settings
from adaptive_rag.contextualization import DeterministicContextualizer
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    GlobalChatModel,
    GlobalChatRetrievalSettings,
    ProviderConnection,
    ProviderSecret,
    RuntimeSlotDefault,
    Workspace,
    WorkspaceChatModel,
    WorkspaceChatRetrievalSettings,
    WorkspaceRuntimeSlotOverride,
)
from adaptive_rag.db.repositories import (
    ProviderConnectionRepository,
    RuntimeSettingsRepository,
    WorkspaceRepository,
    WorkspaceRuntimeSettingsRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.embeddings import QwenDenseEmbeddingProvider
from adaptive_rag.embeddings.qwen import QwenHTTPEmbeddingClient
from adaptive_rag.provider_runtime import (
    ProviderConfigurationError,
    ResolvedRuntimeSlot,
    get_chat_runner,
    get_contextualizer,
    get_dense_embedding_provider,
    get_vision_chat_runner,
)
from adaptive_rag.provider_secrets import ProviderSecretStore


def _settings(**overrides):
    return Settings(_env_file=None, **overrides)


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Workspace.__table__,
            ProviderConnection.__table__,
            ProviderSecret.__table__,
            RuntimeSlotDefault.__table__,
            GlobalChatModel.__table__,
            GlobalChatRetrievalSettings.__table__,
            WorkspaceRuntimeSlotOverride.__table__,
            WorkspaceChatModel.__table__,
            WorkspaceChatRetrievalSettings.__table__,
        ],
    )
    return create_session_factory(engine)()


def _secret_store() -> ProviderSecretStore:
    key = base64.urlsafe_b64encode(b"2" * 32).decode("ascii")
    return ProviderSecretStore(key)


def test_workspace_chat_override_wins_over_global_and_env_without_local_secret() -> (
    None
):
    session = _make_session()
    secret_store = _secret_store()
    workspace = WorkspaceRepository(session).create(name="demo")
    connections = ProviderConnectionRepository(session)
    connections.upsert_connection(
        connection_id="qwen-hosted",
        provider="qwen",
        connection_type="hosted",
        base_url="https://dashscope.example.test/compatible-mode/v1",
        capabilities=["chat"],
    )
    connections.upsert_secret(
        connection_id="qwen-hosted",
        secret_name="api_key",
        secret_value="sk-hosted",
        secret_store=secret_store,
    )
    connections.upsert_connection(
        connection_id="local-chat",
        provider="local_openai_compatible",
        connection_type="local",
        base_url="http://localhost:11434/v1",
        capabilities=["chat"],
    )
    RuntimeSettingsRepository(session).upsert_chat_model(
        connection_id="qwen-hosted",
        model_id="qwen-plus",
    )
    WorkspaceRuntimeSettingsRepository(session).upsert_chat_model(
        workspace_id=workspace.id,
        connection_id="local-chat",
        model_id="llama3.1:8b",
        make_default=True,
    )
    session.commit()

    runner = get_chat_runner(
        _settings(
            provider_runtime_mode="live",
            chat_provider="qwen",
            chat_model="env-chat-model",
            qwen_api_key="sk-env",
            qwen_base_url="https://env.example.test/v1",
        ),
        workspace_id=workspace.id,
        secret_store=secret_store,
        session=session,
    )

    assert isinstance(runner, QwenChatRunner)
    assert runner.provider_name == "local_openai_compatible"
    assert runner.model_name == "llama3.1:8b"
    assert isinstance(runner.client, QwenHTTPChatClient)
    assert runner.client.base_url == "http://localhost:11434/v1"


def test_global_dense_slot_wins_over_env_and_uses_persisted_secret() -> None:
    session = _make_session()
    secret_store = _secret_store()
    workspace = WorkspaceRepository(session).create(name="demo")
    connections = ProviderConnectionRepository(session)
    connections.upsert_connection(
        connection_id="qwen-hosted",
        provider="qwen",
        connection_type="hosted",
        base_url="https://dashscope.example.test/compatible-mode/v1",
        capabilities=["dense_embedding"],
    )
    connections.upsert_secret(
        connection_id="qwen-hosted",
        secret_name="api_key",
        secret_value="sk-db",
        secret_store=secret_store,
    )
    RuntimeSettingsRepository(session).upsert_slot_default(
        slot="dense_embedding",
        connection_id="qwen-hosted",
        model_id="text-embedding-v4",
    )
    session.commit()

    provider = get_dense_embedding_provider(
        _settings(
            provider_runtime_mode="live",
            embedding_provider="qwen",
            embedding_model="env-embedding-model",
            qwen_api_key="sk-env",
            qwen_base_url="https://env.example.test/v1",
        ),
        workspace_id=workspace.id,
        secret_store=secret_store,
        session=session,
    )

    assert isinstance(provider, QwenDenseEmbeddingProvider)
    assert provider.model_name == "text-embedding-v4"
    assert isinstance(provider.client, QwenHTTPEmbeddingClient)
    assert provider.client.api_key == "sk-db"
    assert (
        provider.client.base_url == "https://dashscope.example.test/compatible-mode/v1"
    )


def test_global_chat_default_resolves_without_workspace_id() -> None:
    session = _make_session()
    connections = ProviderConnectionRepository(session)
    connections.upsert_connection(
        connection_id="local-chat",
        provider="local_openai_compatible",
        connection_type="local",
        base_url="http://localhost:11434/v1",
        capabilities=["chat"],
    )
    RuntimeSettingsRepository(session).upsert_chat_model(
        connection_id="local-chat",
        model_id="llama3.1:8b",
        make_default=True,
    )
    session.commit()

    runner = get_chat_runner(
        _settings(
            provider_runtime_mode="live",
            chat_provider="qwen",
            chat_model="env-chat-model",
            qwen_api_key="sk-env",
        ),
        session=session,
    )

    assert isinstance(runner, QwenChatRunner)
    assert runner.provider_name == "local_openai_compatible"
    assert runner.model_name == "llama3.1:8b"
    assert isinstance(runner.client, QwenHTTPChatClient)
    assert runner.client.base_url == "http://localhost:11434/v1"


def test_resolved_runtime_slot_repr_hides_api_key() -> None:
    slot = ResolvedRuntimeSlot(
        slot="chat",
        provider="qwen",
        connection_id="qwen-hosted",
        model_id="qwen-plus",
        base_url="https://example.test/v1",
        parameters=None,
        api_key="sk-secret-value",
    )

    representation = repr(slot)

    assert "qwen-hosted" in representation
    assert "sk-secret-value" not in representation


def test_runtime_resolution_falls_back_to_env_when_no_persisted_setting() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")

    runner = get_chat_runner(
        _settings(
            provider_runtime_mode="live",
            chat_provider="qwen",
            chat_model="qwen-plus-env",
            qwen_api_key="sk-env",
            qwen_base_url="https://env.example.test/v1",
        ),
        workspace_id=workspace.id,
        session=session,
    )

    assert isinstance(runner, QwenChatRunner)
    assert runner.provider_name == "qwen"
    assert runner.model_name == "qwen-plus-env"
    assert isinstance(runner.client, QwenHTTPChatClient)
    assert runner.client.base_url == "https://env.example.test/v1"


def test_runtime_resolution_rejects_hosted_slot_without_persisted_secret() -> None:
    session = _make_session()
    secret_store = _secret_store()
    workspace = WorkspaceRepository(session).create(name="demo")
    ProviderConnectionRepository(session).upsert_connection(
        connection_id="qwen-hosted",
        provider="qwen",
        connection_type="hosted",
        base_url="https://dashscope.example.test/compatible-mode/v1",
        capabilities=["dense_embedding"],
    )
    RuntimeSettingsRepository(session).upsert_slot_default(
        slot="dense_embedding",
        connection_id="qwen-hosted",
        model_id="text-embedding-v4",
    )
    session.commit()

    with pytest.raises(
        ProviderConfigurationError,
        match="missing_provider_secret: qwen-hosted api_key is required",
    ):
        get_dense_embedding_provider(
            _settings(provider_runtime_mode="fake"),
            workspace_id=workspace.id,
            secret_store=secret_store,
            session=session,
        )


def test_contextualizer_resolves_fake_runtime_slot() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    ProviderConnectionRepository(session).upsert_connection(
        connection_id="fake-context",
        provider="fake",
        connection_type="fake",
        capabilities=["contextualization"],
    )
    RuntimeSettingsRepository(session).upsert_slot_default(
        slot="contextualization",
        connection_id="fake-context",
        model_id="deterministic-context-v1",
    )
    session.commit()

    contextualizer = get_contextualizer(
        _settings(provider_runtime_mode="live"),
        workspace_id=workspace.id,
        session=session,
    )

    assert isinstance(contextualizer, DeterministicContextualizer)
    assert contextualizer.provider_name == "local"
    assert contextualizer.model_name == "deterministic-context-v1"


def test_vision_chat_runner_returns_none_when_slot_unconfigured() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")

    runner = get_vision_chat_runner(
        _settings(provider_runtime_mode="live"),
        workspace_id=workspace.id,
        session=session,
    )

    assert runner is None


def test_vision_chat_runner_builds_from_configured_slot() -> None:
    session = _make_session()
    connections = ProviderConnectionRepository(session)
    connections.upsert_connection(
        connection_id="local-vision",
        provider="local_openai_compatible",
        connection_type="local",
        base_url="http://localhost:11434/v1",
        capabilities=["vision"],
    )
    RuntimeSettingsRepository(session).upsert_slot_default(
        slot="vision",
        connection_id="local-vision",
        model_id="qwen2.5-vl-72b",
    )
    session.commit()

    runner = get_vision_chat_runner(
        _settings(provider_runtime_mode="live"),
        session=session,
    )

    assert isinstance(runner, QwenChatRunner)
    assert runner.provider_name == "local_openai_compatible"
    assert runner.model_name == "qwen2.5-vl-72b"
    assert isinstance(runner.client, QwenHTTPChatClient)
    assert runner.client.base_url == "http://localhost:11434/v1"


def test_vision_chat_runner_returns_none_when_slot_incomplete() -> None:
    session = _make_session()
    secret_store = _secret_store()
    connections = ProviderConnectionRepository(session)
    connections.upsert_connection(
        connection_id="qwen-hosted",
        provider="qwen",
        connection_type="hosted",
        base_url="https://dashscope.example.test/compatible-mode/v1",
        capabilities=["vision"],
    )
    RuntimeSettingsRepository(session).upsert_slot_default(
        slot="vision",
        connection_id="qwen-hosted",
        model_id="qwen3-vl-plus",
    )
    session.commit()

    runner = get_vision_chat_runner(
        _settings(provider_runtime_mode="live"),
        secret_store=secret_store,
        session=session,
    )

    assert runner is None
