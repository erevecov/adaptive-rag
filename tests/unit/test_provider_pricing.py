"""Unit tests for Alibaba/Qwen model pricing catalog and sync job."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import ProviderConnection, ProviderModelCatalog
from adaptive_rag.db.repositories import (
    ProviderConnectionRepository,
    ProviderModelCatalogRepository,
)
from adaptive_rag.db.session import create_session_factory
from adaptive_rag.provider_pricing import (
    PRICING_AS_OF,
    PRICING_SOURCE,
    known_qwen_pricing_model_ids,
    lookup_qwen_pricing,
    sync_provider_model_pricing,
)


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[ProviderConnection.__table__, ProviderModelCatalog.__table__],
    )
    return create_session_factory(engine)()


def test_lookup_qwen_pricing_core_product_models() -> None:
    plus = lookup_qwen_pricing("qwen-plus")
    assert plus is not None
    assert plus["input_per_million_tokens_usd"] == 0.4
    assert plus["output_per_million_tokens_usd"] == 1.2
    assert plus["output_thinking_per_million_tokens_usd"] == 4.0
    assert plus["source"] == PRICING_SOURCE
    assert plus["as_of"] == PRICING_AS_OF
    assert plus["currency"] == "USD"

    embed = lookup_qwen_pricing("text-embedding-v4")
    assert embed is not None
    assert embed["input_per_million_tokens_usd"] == 0.07
    assert "output_per_million_tokens_usd" not in embed

    rerank = lookup_qwen_pricing("qwen3-rerank")
    assert rerank is not None
    assert rerank["input_per_million_tokens_usd"] == 0.1

    defaults_chat = lookup_qwen_pricing("qwen3.7-plus")
    assert defaults_chat is not None
    assert defaults_chat["input_per_million_tokens_usd"] == 0.4
    assert defaults_chat["output_per_million_tokens_usd"] == 1.6


def test_lookup_covers_catalog_third_party_and_media_models() -> None:
    deepseek = lookup_qwen_pricing("deepseek-v4-pro")
    assert deepseek is not None
    assert deepseek["input_per_million_tokens_usd"] == 2.4
    assert deepseek["output_per_million_tokens_usd"] == 4.8

    flash_alias = lookup_qwen_pricing("deepseek-v4-flash-0731")
    assert flash_alias is not None
    assert flash_alias["input_per_million_tokens_usd"] == 0.2

    glm = lookup_qwen_pricing("glm-5.2")
    assert glm is not None
    assert glm["input_per_million_tokens_usd"] == 1.4

    flagship = lookup_qwen_pricing("qwen3.8-max")
    assert flagship is not None
    assert flagship["input_per_million_tokens_usd"] == 2.0
    assert flagship["output_per_million_tokens_usd"] == 6.0

    image = lookup_qwen_pricing("wan2.7-image")
    assert image is not None
    assert image["usd_per_image"] == 0.03
    assert "input_per_million_tokens_usd" not in image

    tts = lookup_qwen_pricing("qwen-audio-3.0-tts-plus")
    assert tts is not None
    assert tts["input_per_10k_characters_usd"] == 0.2


def test_lookup_qwen_pricing_normalizes_case_and_whitespace() -> None:
    assert lookup_qwen_pricing("  Qwen-Plus  ") == lookup_qwen_pricing("qwen-plus")


def test_lookup_qwen_pricing_unknown_returns_none() -> None:
    assert lookup_qwen_pricing("totally-unknown-model-xyz") is None
    assert lookup_qwen_pricing("") is None
    assert lookup_qwen_pricing("   ") is None
    # Realtime audio: Singapore list not published in model-pricing tables we use.
    assert lookup_qwen_pricing("qwen-audio-3.0-realtime-plus") is None


def test_known_model_ids_include_product_defaults() -> None:
    ids = known_qwen_pricing_model_ids()
    assert "qwen-plus" in ids
    assert "text-embedding-v4" in ids
    assert "qwen3-rerank" in ids
    assert "deepseek-v4-pro" in ids
    assert "glm-5.2" in ids
    assert "wan2.7-image" in ids
    assert "qwen3.8-max" in ids


def test_sync_updates_qwen_catalog_and_skips_fake_and_unknown() -> None:
    session = _make_session()
    connections = ProviderConnectionRepository(session)
    catalog = ProviderModelCatalogRepository(session)

    connections.upsert_connection(
        connection_id="qwen-hosted",
        provider="qwen",
        connection_type="hosted",
        base_url="https://dashscope.example.test/compatible-mode/v1",
        capabilities=["chat", "dense_embedding", "rerank"],
    )
    connections.upsert_connection(
        connection_id="fake-local",
        provider="fake",
        connection_type="fake",
        capabilities=["chat"],
    )
    catalog.upsert_model(
        connection_id="qwen-hosted",
        model_id="qwen-plus",
        capabilities=["chat"],
        pricing=None,
    )
    catalog.upsert_model(
        connection_id="qwen-hosted",
        model_id="text-embedding-v4",
        capabilities=["dense_embedding"],
        pricing={"input_per_million_tokens_usd": 0.07},  # stale partial shape
    )
    catalog.upsert_model(
        connection_id="qwen-hosted",
        model_id="experimental-preview-xyz",
        capabilities=["chat"],
        pricing=None,
    )
    catalog.upsert_model(
        connection_id="fake-local",
        model_id="retrieval-grounded-local-v1",
        capabilities=["chat"],
        pricing=None,
    )
    session.commit()

    report = sync_provider_model_pricing(session, dry_run=False)
    session.commit()

    assert report.connections_seen == 1
    assert report.models_seen == 3
    assert report.updated == 2  # qwen-plus + text-embedding-v4
    assert report.skipped_unknown == 1
    assert report.skipped_non_target_provider == 1
    assert report.unchanged == 0
    assert report.dry_run is False

    plus = session.get(ProviderModelCatalog, ("qwen-hosted", "qwen-plus"))
    assert plus is not None
    assert plus.pricing_json is not None
    assert plus.pricing_json["input_per_million_tokens_usd"] == 0.4
    assert plus.pricing_json["output_per_million_tokens_usd"] == 1.2
    assert plus.pricing_json["source"] == PRICING_SOURCE

    embed = session.get(ProviderModelCatalog, ("qwen-hosted", "text-embedding-v4"))
    assert embed is not None
    assert embed.pricing_json is not None
    assert embed.pricing_json["input_per_million_tokens_usd"] == 0.07
    assert embed.pricing_json["as_of"] == PRICING_AS_OF

    unknown = session.get(
        ProviderModelCatalog, ("qwen-hosted", "experimental-preview-xyz")
    )
    assert unknown is not None
    assert unknown.pricing_json is None

    fake = session.get(
        ProviderModelCatalog, ("fake-local", "retrieval-grounded-local-v1")
    )
    assert fake is not None
    assert fake.pricing_json is None


def test_sync_is_idempotent_when_pricing_already_current() -> None:
    session = _make_session()
    connections = ProviderConnectionRepository(session)
    catalog = ProviderModelCatalogRepository(session)

    connections.upsert_connection(
        connection_id="qwen-hosted",
        provider="qwen",
        connection_type="hosted",
        capabilities=["chat"],
    )
    pricing = lookup_qwen_pricing("qwen-plus")
    assert pricing is not None
    catalog.upsert_model(
        connection_id="qwen-hosted",
        model_id="qwen-plus",
        capabilities=["chat"],
        pricing=pricing,
    )
    session.commit()

    report = sync_provider_model_pricing(session, dry_run=False)
    session.commit()

    assert report.updated == 0
    assert report.unchanged == 1
    assert report.models_seen == 1


def test_sync_dry_run_does_not_persist() -> None:
    session = _make_session()
    connections = ProviderConnectionRepository(session)
    catalog = ProviderModelCatalogRepository(session)

    connections.upsert_connection(
        connection_id="qwen-hosted",
        provider="qwen",
        connection_type="hosted",
        capabilities=["chat"],
    )
    catalog.upsert_model(
        connection_id="qwen-hosted",
        model_id="qwen-plus",
        capabilities=["chat"],
        pricing=None,
    )
    session.commit()

    report = sync_provider_model_pricing(session, dry_run=True)
    session.commit()

    assert report.updated == 1
    assert report.dry_run is True
    row = session.get(ProviderModelCatalog, ("qwen-hosted", "qwen-plus"))
    assert row is not None
    assert row.pricing_json is None


def test_sync_rejects_non_qwen_provider_flag() -> None:
    session = _make_session()
    with pytest.raises(ValueError, match="unsupported pricing provider"):
        sync_provider_model_pricing(session, provider="openai")


def test_upsert_model_preserves_existing_pricing_when_listing_omits_it() -> None:
    session = _make_session()
    connections = ProviderConnectionRepository(session)
    catalog = ProviderModelCatalogRepository(session)
    connections.upsert_connection(
        connection_id="qwen-hosted",
        provider="qwen",
        connection_type="hosted",
        capabilities=["chat"],
    )
    catalog.upsert_model(
        connection_id="qwen-hosted",
        model_id="qwen-plus",
        capabilities=["chat"],
        pricing={"input_per_million_tokens_usd": 0.4},
    )
    session.commit()

    catalog.upsert_model(
        connection_id="qwen-hosted",
        model_id="qwen-plus",
        capabilities=["chat", "contextualization"],
        pricing=None,
    )
    session.commit()

    row = session.get(ProviderModelCatalog, ("qwen-hosted", "qwen-plus"))
    assert row is not None
    assert row.capabilities_json == ["chat", "contextualization"]
    assert row.pricing_json == {"input_per_million_tokens_usd": 0.4}


def test_update_model_pricing_only_touches_pricing_json() -> None:
    session = _make_session()
    connections = ProviderConnectionRepository(session)
    catalog = ProviderModelCatalogRepository(session)
    connections.upsert_connection(
        connection_id="qwen-hosted",
        provider="qwen",
        connection_type="hosted",
        capabilities=["chat"],
    )
    catalog.upsert_model(
        connection_id="qwen-hosted",
        model_id="qwen-plus",
        capabilities=["chat"],
        metadata={"owned_by": "system"},
        pricing=None,
    )
    session.commit()
    before = session.get(ProviderModelCatalog, ("qwen-hosted", "qwen-plus"))
    assert before is not None
    last_seen = before.last_seen_at

    updated = catalog.update_model_pricing(
        connection_id="qwen-hosted",
        model_id="qwen-plus",
        pricing=lookup_qwen_pricing("qwen-plus"),
    )
    session.commit()

    assert updated is not None
    assert updated.pricing_json is not None
    assert updated.pricing_json["input_per_million_tokens_usd"] == 0.4
    assert updated.metadata_json == {"owned_by": "system"}
    assert updated.capabilities_json == ["chat"]
    assert updated.last_seen_at == last_seen
    assert (
        catalog.update_model_pricing(
            connection_id="qwen-hosted",
            model_id="missing",
            pricing={"input_per_million_tokens_usd": 1.0},
        )
        is None
    )
