"""Tests for global runtime slot defaults and chat model pool repository."""

from __future__ import annotations

import pytest

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    GlobalChatModel,
    ProviderConnection,
    RuntimeSlotDefault,
)
from adaptive_rag.db.repositories import (
    ProviderConnectionRepository,
    RuntimeSettingsRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            ProviderConnection.__table__,
            RuntimeSlotDefault.__table__,
            GlobalChatModel.__table__,
        ],
    )
    return create_session_factory(engine)()


def _add_connection(
    session,
    *,
    connection_id: str,
    provider: str = "qwen",
    connection_type: str = "hosted",
    capabilities: list[str],
    base_url: str | None = None,
) -> None:
    ProviderConnectionRepository(session).upsert_connection(
        connection_id=connection_id,
        provider=provider,
        connection_type=connection_type,
        base_url=base_url,
        capabilities=capabilities,
    )


def test_repository_upserts_and_lists_global_slot_defaults() -> None:
    session = _make_session()
    _add_connection(
        session,
        connection_id="qwen-hosted",
        capabilities=["dense_embedding", "sparse_embedding", "rerank"],
    )
    _add_connection(
        session,
        connection_id="local-chat",
        provider="local_openai_compatible",
        connection_type="local",
        capabilities=["chat"],
        base_url="http://localhost:11434/v1",
    )
    repository = RuntimeSettingsRepository(session)

    rerank = repository.upsert_slot_default(
        slot="rerank",
        connection_id="qwen-hosted",
        model_id="qwen3-rerank",
        parameters={"top_n": 8},
    )
    chat = repository.upsert_slot_default(
        slot="chat",
        connection_id="local-chat",
        model_id="qwen2.5:14b",
    )
    session.commit()

    defaults = repository.list_slot_defaults()

    assert [default.slot for default in defaults] == ["chat", "rerank"]
    assert rerank.parameters_json == {"top_n": 8}
    assert chat.connection_id == "local-chat"


def test_repository_rejects_unknown_slot_and_incompatible_connection() -> None:
    session = _make_session()
    _add_connection(session, connection_id="chat-only", capabilities=["chat"])
    repository = RuntimeSettingsRepository(session)

    with pytest.raises(ValueError, match="unsupported_slot"):
        repository.upsert_slot_default(
            slot="voice",
            connection_id="chat-only",
            model_id="voice-model",
        )

    with pytest.raises(ValueError, match="connection_unavailable"):
        repository.upsert_slot_default(
            slot="rerank",
            connection_id="chat-only",
            model_id="qwen3-rerank",
        )

    assert repository.list_slot_defaults() == []


def test_chat_model_pool_rotates_exactly_one_default_and_syncs_chat_slot() -> None:
    session = _make_session()
    _add_connection(
        session,
        connection_id="local-chat",
        provider="local_openai_compatible",
        connection_type="local",
        capabilities=["chat"],
        base_url="http://localhost:11434/v1",
    )
    _add_connection(session, connection_id="qwen-hosted", capabilities=["chat"])
    repository = RuntimeSettingsRepository(session)

    first = repository.upsert_chat_model(
        connection_id="local-chat",
        model_id="qwen2.5:14b",
    )
    second = repository.upsert_chat_model(
        connection_id="qwen-hosted",
        model_id="qwen-plus",
        make_default=True,
    )
    session.commit()

    models = repository.list_chat_models()
    default = repository.get_slot_default("chat")

    assert first.is_default is False
    assert second.is_default is True
    model_states = [
        (model.connection_id, model.model_id, model.is_default) for model in models
    ]

    assert model_states == [
        ("qwen-hosted", "qwen-plus", True),
        ("local-chat", "qwen2.5:14b", False),
    ]
    assert default is not None
    assert default.connection_id == "qwen-hosted"
    assert default.model_id == "qwen-plus"


def test_chat_model_pool_rejects_deleting_last_or_default_model() -> None:
    session = _make_session()
    _add_connection(session, connection_id="qwen-hosted", capabilities=["chat"])
    _add_connection(
        session,
        connection_id="local-chat",
        provider="local_openai_compatible",
        connection_type="local",
        capabilities=["chat"],
    )
    repository = RuntimeSettingsRepository(session)
    repository.upsert_chat_model(connection_id="qwen-hosted", model_id="qwen-plus")
    session.commit()

    with pytest.raises(ValueError, match="cannot_delete_last_chat_model"):
        repository.delete_chat_model(connection_id="qwen-hosted", model_id="qwen-plus")

    repository.upsert_chat_model(connection_id="local-chat", model_id="llama3.1:8b")
    session.commit()

    with pytest.raises(ValueError, match="cannot_delete_default_chat_model"):
        repository.delete_chat_model(connection_id="qwen-hosted", model_id="qwen-plus")

    deleted = repository.delete_chat_model(
        connection_id="local-chat",
        model_id="llama3.1:8b",
    )

    assert deleted is True
