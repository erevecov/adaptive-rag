"""Tests for global provider connection repository behavior."""

from __future__ import annotations

import base64

import pytest

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import ProviderConnection, ProviderSecret
from adaptive_rag.db.repositories import ProviderConnectionRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.provider_secrets import ProviderSecretStore


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[ProviderConnection.__table__, ProviderSecret.__table__],
    )
    return create_session_factory(engine)()


def _secret_store() -> ProviderSecretStore:
    key = base64.urlsafe_b64encode(b"1" * 32).decode("ascii")
    return ProviderSecretStore(key)


def test_repository_upserts_hosted_and_local_connections_side_by_side() -> None:
    session = _make_session()
    repository = ProviderConnectionRepository(session)

    hosted = repository.upsert_connection(
        connection_id="qwen-hosted",
        provider="qwen",
        connection_type="hosted",
        base_url="https://dashscope.example.test/compatible-mode/v1",
        capabilities=["dense_embedding", "sparse_embedding", "rerank"],
        metadata={"label": "Qwen hosted"},
    )
    local = repository.upsert_connection(
        connection_id="local-chat",
        provider="local_openai_compatible",
        connection_type="local",
        base_url="http://localhost:11434/v1",
        capabilities=["chat"],
    )
    session.commit()

    connections = repository.list_connections()

    assert [connection.connection_id for connection in connections] == [
        "local-chat",
        "qwen-hosted",
    ]
    assert hosted.provider == "qwen"
    assert local.connection_type == "local"


def test_repository_encrypts_secret_and_returns_status_only() -> None:
    session = _make_session()
    repository = ProviderConnectionRepository(session)
    repository.upsert_connection(
        connection_id="qwen-hosted",
        provider="qwen",
        connection_type="hosted",
        base_url="https://dashscope.example.test/compatible-mode/v1",
        capabilities=["chat"],
    )

    status = repository.upsert_secret(
        connection_id="qwen-hosted",
        secret_name="api_key",
        secret_value="sk-hosted-secret",
        secret_store=_secret_store(),
    )
    session.commit()

    row = session.get(ProviderSecret, ("qwen-hosted", "api_key"))

    assert row is not None
    assert row.encrypted_value != b"sk-hosted-secret"
    assert b"sk-hosted-secret" not in row.encrypted_value
    assert status.configured is True
    assert status.last_four == "cret"
    assert status.fingerprint is not None
    assert "sk-hosted-secret" not in repr(status)


def test_repository_deletes_connection_and_secrets_portably() -> None:
    session = _make_session()
    repository = ProviderConnectionRepository(session)
    repository.upsert_connection(
        connection_id="qwen-hosted",
        provider="qwen",
        connection_type="hosted",
        capabilities=["chat"],
    )
    repository.upsert_secret(
        connection_id="qwen-hosted",
        secret_name="api_key",
        secret_value="sk-hosted-secret",
        secret_store=_secret_store(),
    )
    session.commit()

    deleted = repository.delete_connection("qwen-hosted")
    session.commit()

    assert deleted is True
    assert session.get(ProviderConnection, "qwen-hosted") is None
    assert session.get(ProviderSecret, ("qwen-hosted", "api_key")) is None


def test_repository_rejects_unknown_capability_before_persisting() -> None:
    session = _make_session()
    repository = ProviderConnectionRepository(session)

    with pytest.raises(ValueError, match="unsupported provider capability"):
        repository.upsert_connection(
            connection_id="bad",
            provider="qwen",
            connection_type="hosted",
            capabilities=["chat", "voice"],
        )

    assert repository.list_connections() == []
