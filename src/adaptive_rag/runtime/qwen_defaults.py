"""Qwen production defaults and catalog-driven materialization."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from adaptive_rag.db.models import ProviderConnection, ProviderModelCatalog
from adaptive_rag.db.repositories import (
    ProviderModelCatalogRepository,
    RuntimeSettingsRepository,
)

QWEN_CHAT_MODEL_ID = "qwen-plus"
QWEN_EMBEDDING_MODEL_ID = "text-embedding-v4"
QWEN_RERANK_MODEL_ID = "qwen3-rerank"

_QWEN_EMBEDDING_MODEL_IDS = {"text-embedding-v3", "text-embedding-v4"}
_QWEN_CHAT_MODEL_IDS = {"qwen-plus", "qwen-max", "qwen-turbo"}


@dataclass(frozen=True, slots=True)
class QwenRuntimeDefaultsReport:
    """Summary of Qwen defaults configured during materialization."""

    configured_chat_default: bool
    configured_slot_defaults: tuple[str, ...]


def infer_qwen_model_capabilities(model_id: str) -> tuple[str, ...]:
    """Infer safe slot capabilities for known Qwen model IDs."""

    normalized = model_id.strip().lower()
    if normalized in _QWEN_EMBEDDING_MODEL_IDS:
        return ("dense_embedding", "sparse_embedding")
    if "rerank" in normalized:
        return ("rerank",)
    if normalized in _QWEN_CHAT_MODEL_IDS:
        return ("chat",)
    if normalized.startswith("qwen3-") and "embedding" not in normalized:
        return ("chat",)
    return ()


def materialize_qwen_runtime_defaults(
    session: Session,
) -> QwenRuntimeDefaultsReport:
    """Configure missing Qwen runtime defaults from connected model catalog rows."""

    runtime = RuntimeSettingsRepository(session)
    configured_chat_default = False
    configured_slot_defaults: list[str] = []

    if not runtime.list_chat_models() and runtime.get_slot_default("chat") is None:
        candidate = _qwen_catalog_candidate(
            session,
            model_id=QWEN_CHAT_MODEL_ID,
            capability="chat",
        )
        if candidate is not None:
            runtime.upsert_chat_model(
                connection_id=candidate.connection_id,
                model_id=candidate.model_id,
                make_default=True,
            )
            configured_chat_default = True

    if runtime.get_slot_default("dense_embedding") is None:
        candidate = _qwen_catalog_candidate(
            session,
            model_id=QWEN_EMBEDDING_MODEL_ID,
            capability="dense_embedding",
        )
        if candidate is not None:
            runtime.upsert_slot_default(
                slot="dense_embedding",
                connection_id=candidate.connection_id,
                model_id=candidate.model_id,
            )
            configured_slot_defaults.append("dense_embedding")

    if runtime.get_slot_default("sparse_embedding") is None:
        candidate = _qwen_catalog_candidate(
            session,
            model_id=QWEN_EMBEDDING_MODEL_ID,
            capability="sparse_embedding",
            require_native_sparse_endpoint=True,
        )
        if candidate is not None:
            runtime.upsert_slot_default(
                slot="sparse_embedding",
                connection_id=candidate.connection_id,
                model_id=candidate.model_id,
            )
            configured_slot_defaults.append("sparse_embedding")

    if runtime.get_slot_default("rerank") is None:
        candidate = _qwen_catalog_candidate(
            session,
            model_id=QWEN_RERANK_MODEL_ID,
            capability="rerank",
        )
        if candidate is not None:
            runtime.upsert_slot_default(
                slot="rerank",
                connection_id=candidate.connection_id,
                model_id=candidate.model_id,
            )
            configured_slot_defaults.append("rerank")

    session.flush()
    return QwenRuntimeDefaultsReport(
        configured_chat_default=configured_chat_default,
        configured_slot_defaults=tuple(configured_slot_defaults),
    )


def is_qwen_native_sparse_base_url(base_url: str | None) -> bool:
    """Return whether a Qwen base URL can serve native sparse embeddings."""

    if base_url is None:
        return False
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        return False
    if "/compatible-mode/" in normalized or normalized.endswith("/v1"):
        return False
    return "/services/embeddings/text-embedding" in normalized


def _qwen_catalog_candidate(
    session: Session,
    *,
    model_id: str,
    capability: str,
    require_native_sparse_endpoint: bool = False,
) -> ProviderModelCatalog | None:
    models = ProviderModelCatalogRepository(session).list_models(capability=capability)
    for model in models:
        if model.model_id != model_id:
            continue
        connection = session.get(ProviderConnection, model.connection_id)
        if connection is None or connection.provider != "qwen":
            continue
        if capability not in connection.capabilities_json:
            continue
        if require_native_sparse_endpoint and not is_qwen_native_sparse_base_url(
            connection.base_url
        ):
            continue
        return model
    return None
