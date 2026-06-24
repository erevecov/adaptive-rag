"""Tests for global provider connection persistence models."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import ProviderConnection, ProviderSecret
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[ProviderConnection.__table__, ProviderSecret.__table__],
    )
    return create_session_factory(engine)()


def test_provider_connection_persists_global_connection_metadata() -> None:
    session = _make_session()
    connection = ProviderConnection(
        connection_id="qwen-hosted",
        provider="qwen",
        connection_type="hosted",
        base_url="https://dashscope.example.test/compatible-mode/v1",
        capabilities_json=["chat", "dense_embedding", "rerank"],
        metadata_json={"label": "Qwen hosted"},
    )

    session.add(connection)
    session.commit()
    session.expunge_all()

    fetched = session.get(ProviderConnection, "qwen-hosted")

    assert fetched is not None
    assert fetched.provider == "qwen"
    assert fetched.connection_type == "hosted"
    assert fetched.capabilities_json == ["chat", "dense_embedding", "rerank"]
    assert fetched.metadata_json == {"label": "Qwen hosted"}


def test_provider_secret_uses_composite_identity_and_binary_value() -> None:
    columns = {column.name: column for column in inspect(ProviderSecret).columns}

    assert columns["connection_id"].primary_key
    assert columns["secret_name"].primary_key
    assert columns["encrypted_value"].nullable is False


def test_provider_connection_rejects_unsupported_provider_and_type() -> None:
    session = _make_session()
    connection = ProviderConnection(
        connection_id="bad",
        provider="unknown",
        connection_type="hosted",
        capabilities_json=["chat"],
    )

    try:
        session.add(connection)
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for unsupported provider")
