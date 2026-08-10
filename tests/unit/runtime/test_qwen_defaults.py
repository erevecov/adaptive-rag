"""Tests for Qwen runtime default materialization."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    GlobalChatModel,
    ProviderConnection,
    ProviderModelCatalog,
    RuntimeSlotDefault,
)
from adaptive_rag.db.repositories import RuntimeSettingsRepository
from adaptive_rag.db.session import create_session_factory
from adaptive_rag.runtime.qwen_defaults import (
    ensure_qwen_declared_capability_models,
    infer_qwen_model_capabilities,
    is_qwen_native_sparse_base_url,
    materialize_qwen_runtime_defaults,
)


def _session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            ProviderConnection.__table__,
            ProviderModelCatalog.__table__,
            RuntimeSlotDefault.__table__,
            GlobalChatModel.__table__,
        ],
    )
    return create_session_factory(engine)()


def _add_connection(
    session: Session,
    *,
    connection_id: str,
    provider: str = "qwen",
    connection_type: str = "hosted",
    base_url: str = "https://dashscope.example.test/compatible-mode/v1",
    capabilities: list[str] | None = None,
) -> None:
    session.add(
        ProviderConnection(
            connection_id=connection_id,
            provider=provider,
            connection_type=connection_type,
            base_url=base_url,
            capabilities_json=capabilities
            or ["chat", "dense_embedding", "sparse_embedding", "rerank"],
            metadata_json=None,
        )
    )
    session.flush()


def _add_model(
    session: Session,
    *,
    connection_id: str,
    model_id: str,
    capabilities: list[str],
) -> None:
    session.add(
        ProviderModelCatalog(
            connection_id=connection_id,
            model_id=model_id,
            capabilities_json=capabilities,
            metadata_json=None,
            pricing_json=None,
        )
    )
    session.flush()


def test_seeds_rerank_and_embedding_when_declared_but_missing_from_provider_list() -> (
    None
):
    session = _session()
    _add_connection(
        session,
        connection_id="bailian",
        capabilities=["chat", "dense_embedding", "sparse_embedding", "rerank"],
    )
    # Provider /models only returned a chat model.
    _add_model(
        session,
        connection_id="bailian",
        model_id="qwen3.7-plus",
        capabilities=["chat"],
    )

    connection = session.get(ProviderConnection, "bailian")
    assert connection is not None
    seeded = ensure_qwen_declared_capability_models(session, connection)
    session.commit()

    assert "qwen3-rerank" in seeded
    assert "text-embedding-v4" in seeded
    rerank = session.get(ProviderModelCatalog, ("bailian", "qwen3-rerank"))
    embed = session.get(ProviderModelCatalog, ("bailian", "text-embedding-v4"))
    assert rerank is not None
    assert rerank.capabilities_json == ["rerank"]
    assert embed is not None
    assert set(embed.capabilities_json) == {"dense_embedding", "sparse_embedding"}


def test_infers_known_qwen_model_capabilities() -> None:
    assert infer_qwen_model_capabilities("qwen-plus") == ("chat",)
    assert infer_qwen_model_capabilities("text-embedding-v4") == (
        "dense_embedding",
        "sparse_embedding",
    )
    assert infer_qwen_model_capabilities("qwen3-rerank") == ("rerank",)
    # Modern dotted ids from Bailian Token Plan.
    assert infer_qwen_model_capabilities("qwen3.7-plus") == ("chat",)
    assert infer_qwen_model_capabilities("qwen3.8-max") == ("chat",)
    assert infer_qwen_model_capabilities("qwen3.6-flash") == ("chat",)
    assert infer_qwen_model_capabilities("deepseek-v4-pro") == ("chat",)
    assert infer_qwen_model_capabilities("glm-5.2") == ("chat",)
    assert infer_qwen_model_capabilities("wan2.7-image") == ()
    assert infer_qwen_model_capabilities("qwen-audio-3.0-tts-plus") == ()


def test_infers_vision_capabilities_for_qwen_vl_models() -> None:
    assert infer_qwen_model_capabilities("qwen-vl-max") == ("chat", "vision")
    assert infer_qwen_model_capabilities("qwen2-vl-7b") == ("chat", "vision")
    assert infer_qwen_model_capabilities("qwen2.5-vl-72b") == ("chat", "vision")
    assert infer_qwen_model_capabilities("qwen3-vl-plus") == ("chat", "vision")
    assert infer_qwen_model_capabilities("Qwen2.5-VL-72B-Instruct") == (
        "chat",
        "vision",
    )
    assert infer_qwen_model_capabilities("qwen3-vision-plus") == ("chat", "vision")


def test_does_not_mark_non_vision_qwen_models_as_vision() -> None:
    assert infer_qwen_model_capabilities("qwen-plus") == ("chat",)
    assert infer_qwen_model_capabilities("qwen3-max") == ("chat",)
    assert infer_qwen_model_capabilities("qwen3-embedding-8b") == (
        "dense_embedding",
        "sparse_embedding",
    )
    assert infer_qwen_model_capabilities("qwen3-rerank") == ("rerank",)
    assert infer_qwen_model_capabilities("text-embedding-v4") == (
        "dense_embedding",
        "sparse_embedding",
    )


def test_materializes_qwen_defaults_from_connected_catalog_idempotently() -> None:
    session = _session()
    _add_connection(session, connection_id="qwen-hosted")
    _add_model(
        session,
        connection_id="qwen-hosted",
        model_id="qwen-plus",
        capabilities=["chat"],
    )
    _add_model(
        session,
        connection_id="qwen-hosted",
        model_id="text-embedding-v4",
        capabilities=["dense_embedding", "sparse_embedding"],
    )
    _add_model(
        session,
        connection_id="qwen-hosted",
        model_id="qwen3-rerank",
        capabilities=["rerank"],
    )

    materialize_qwen_runtime_defaults(session)
    counts_after_first = (
        session.query(GlobalChatModel).count(),
        session.query(RuntimeSlotDefault).count(),
    )
    materialize_qwen_runtime_defaults(session)

    chat_model = session.get(GlobalChatModel, ("qwen-hosted", "qwen-plus"))
    chat_default = session.get(RuntimeSlotDefault, "chat")
    dense_default = session.get(RuntimeSlotDefault, "dense_embedding")
    sparse_default = session.get(RuntimeSlotDefault, "sparse_embedding")
    rerank_default = session.get(RuntimeSlotDefault, "rerank")

    assert counts_after_first == (
        session.query(GlobalChatModel).count(),
        session.query(RuntimeSlotDefault).count(),
    )
    assert chat_model is not None
    assert chat_model.is_default is True
    assert chat_default is not None
    assert chat_default.connection_id == "qwen-hosted"
    assert chat_default.model_id == "qwen-plus"
    assert dense_default is not None
    assert dense_default.connection_id == "qwen-hosted"
    assert dense_default.model_id == "text-embedding-v4"
    assert sparse_default is None
    assert rerank_default is not None
    assert rerank_default.connection_id == "qwen-hosted"
    assert rerank_default.model_id == "qwen3-rerank"


def test_materializes_qwen_sparse_default_only_from_native_text_embedding_url() -> None:
    session = _session()
    _add_connection(
        session,
        connection_id="qwen-native-sparse",
        base_url=(
            "https://dashscope.example.test/api/v1/services/embeddings/"
            "text-embedding/text-embedding"
        ),
        capabilities=["sparse_embedding"],
    )
    _add_model(
        session,
        connection_id="qwen-native-sparse",
        model_id="text-embedding-v4",
        capabilities=["sparse_embedding"],
    )

    materialize_qwen_runtime_defaults(session)

    sparse_default = session.get(RuntimeSlotDefault, "sparse_embedding")
    assert sparse_default is not None
    assert sparse_default.connection_id == "qwen-native-sparse"
    assert sparse_default.model_id == "text-embedding-v4"


def test_materializes_qwen_sparse_default_from_dashscope_api_v1_root() -> None:
    """Single DashScope …/api/v1 connection is enough for sparse + rerank slots."""

    session = _session()
    _add_connection(
        session,
        connection_id="qwen-dashscope",
        base_url="https://dashscope.example.test/api/v1",
        capabilities=["dense_embedding", "sparse_embedding", "rerank"],
    )
    _add_model(
        session,
        connection_id="qwen-dashscope",
        model_id="text-embedding-v4",
        capabilities=["dense_embedding", "sparse_embedding"],
    )
    _add_model(
        session,
        connection_id="qwen-dashscope",
        model_id="qwen3-rerank",
        capabilities=["rerank"],
    )

    materialize_qwen_runtime_defaults(session)

    sparse_default = session.get(RuntimeSlotDefault, "sparse_embedding")
    dense_default = session.get(RuntimeSlotDefault, "dense_embedding")
    rerank_default = session.get(RuntimeSlotDefault, "rerank")
    assert sparse_default is not None
    assert sparse_default.connection_id == "qwen-dashscope"
    assert dense_default is not None
    assert dense_default.connection_id == "qwen-dashscope"
    assert rerank_default is not None
    assert rerank_default.connection_id == "qwen-dashscope"


def test_is_qwen_native_sparse_base_url_accepts_api_v1_root() -> None:
    assert is_qwen_native_sparse_base_url(
        "https://dashscope-intl.aliyuncs.com/api/v1"
    )
    assert is_qwen_native_sparse_base_url(
        "https://dashscope.example.test/api/v1/services/embeddings/"
        "text-embedding/text-embedding"
    )
    assert not is_qwen_native_sparse_base_url(
        "https://token-plan.example.test/compatible-mode/v1"
    )
    assert not is_qwen_native_sparse_base_url("http://localhost:11434/v1")


def test_materialize_qwen_defaults_preserves_existing_user_choices() -> None:
    session = _session()
    _add_connection(
        session,
        connection_id="local-all",
        provider="local_openai_compatible",
        connection_type="local",
        base_url="http://localhost:11434/v1",
    )
    runtime = RuntimeSettingsRepository(session)
    runtime.upsert_chat_model(
        connection_id="local-all",
        model_id="qwen2.5:14b",
        make_default=True,
    )
    runtime.upsert_slot_default(
        slot="dense_embedding",
        connection_id="local-all",
        model_id="local-dense",
    )
    runtime.upsert_slot_default(
        slot="sparse_embedding",
        connection_id="local-all",
        model_id="local-sparse",
    )
    runtime.upsert_slot_default(
        slot="rerank",
        connection_id="local-all",
        model_id="local-rerank",
    )
    _add_connection(session, connection_id="qwen-hosted")
    _add_model(
        session,
        connection_id="qwen-hosted",
        model_id="qwen-plus",
        capabilities=["chat"],
    )
    _add_model(
        session,
        connection_id="qwen-hosted",
        model_id="text-embedding-v4",
        capabilities=["dense_embedding", "sparse_embedding"],
    )
    _add_model(
        session,
        connection_id="qwen-hosted",
        model_id="qwen3-rerank",
        capabilities=["rerank"],
    )

    materialize_qwen_runtime_defaults(session)

    assert session.get(GlobalChatModel, ("qwen-hosted", "qwen-plus")) is None
    assert session.get(RuntimeSlotDefault, "chat").connection_id == "local-all"
    assert session.get(RuntimeSlotDefault, "chat").model_id == "qwen2.5:14b"
    assert session.get(RuntimeSlotDefault, "dense_embedding").model_id == "local-dense"
    assert session.get(RuntimeSlotDefault, "sparse_embedding").model_id == (
        "local-sparse"
    )
    assert session.get(RuntimeSlotDefault, "rerank").model_id == "local-rerank"
