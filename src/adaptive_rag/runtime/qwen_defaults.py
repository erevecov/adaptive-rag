"""Qwen production defaults and catalog-driven materialization."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
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
_QWEN_VISION_MODEL_PATTERN = re.compile(r"(?:^|[-_.])vl(?:[-_.]|$)")

# OpenAI-compatible GET /models (Bailian Token Plan, etc.) often omits these
# service models even when the connection declares the slot capability.
_DECLARED_CAPABILITY_SEED_MODELS: dict[str, tuple[str, ...]] = {
    "dense_embedding": (QWEN_EMBEDDING_MODEL_ID,),
    "sparse_embedding": (QWEN_EMBEDDING_MODEL_ID,),
    "rerank": (QWEN_RERANK_MODEL_ID,),
}


@dataclass(frozen=True, slots=True)
class QwenRuntimeDefaultsReport:
    """Summary of Qwen defaults configured during materialization."""

    configured_chat_default: bool
    configured_slot_defaults: tuple[str, ...]


def infer_qwen_model_capabilities(model_id: str) -> tuple[str, ...]:
    """Infer safe slot capabilities for known Qwen / Model Studio model IDs.

    Bailian Token Plan and modern DashScope ids often use dots (``qwen3.7-plus``)
    rather than hyphens (``qwen3-max``). Third-party text models hosted on
    Model Studio (DeepSeek, GLM) are treated as chat.
    """

    normalized = model_id.strip().lower()
    if not normalized:
        return ()
    if normalized in _QWEN_EMBEDDING_MODEL_IDS or (
        "embedding" in normalized and "rerank" not in normalized
    ):
        return ("dense_embedding", "sparse_embedding")
    if "rerank" in normalized:
        return ("rerank",)
    # Image generation (Wan) is not a runtime RAG slot model.
    if normalized.startswith("wan") or "image" in normalized and "vl" not in normalized:
        return ()
    # Audio / TTS / realtime — not chat pipeline slots.
    if "tts" in normalized or "audio" in normalized or "realtime" in normalized:
        return ()
    if _QWEN_VISION_MODEL_PATTERN.search(normalized) or "vision" in normalized:
        # Vision-capable chat models also drive contextualization when declared.
        return ("chat", "contextualization", "vision")
    if normalized in _QWEN_CHAT_MODEL_IDS:
        return ("chat", "contextualization")
    # qwen3-max, qwen3.7-plus, qwen3.8-max, qwen3.6-flash, …
    if normalized.startswith("qwen") and "embedding" not in normalized:
        return ("chat", "contextualization")
    # Third-party LLMs served via Model Studio / Bailian.
    if (
        "deepseek" in normalized
        or normalized.startswith("glm")
        or normalized.startswith("kimi")
        or normalized.startswith("moonshot")
    ):
        return ("chat", "contextualization")
    return ()


def ensure_qwen_declared_capability_models(
    session: Session,
    connection: ProviderConnection,
) -> tuple[str, ...]:
    """Seed well-known models for capabilities that provider /models omits.

    Bailian Token Plan and similar OpenAI-compatible listings return chat LLMs
    but not ``qwen3-rerank`` / ``text-embedding-v4``. When the connection
    declares those slots, insert catalog rows so Global Defaults and Model
    Catalog can select them. Returns seeded model ids (may be empty).
    """

    if connection.provider != "qwen":
        return ()

    catalog = ProviderModelCatalogRepository(session)
    declared = set(connection.capabilities_json)
    seeded: list[str] = []
    for capability, model_ids in _DECLARED_CAPABILITY_SEED_MODELS.items():
        if capability not in declared:
            continue
        for model_id in model_ids:
            inferred = infer_qwen_model_capabilities(model_id)
            capabilities = [cap for cap in inferred if cap in declared]
            if not capabilities:
                continue
            # Sparse-only seed still needs dense+sparse on the embedding model
            # when the connection only declared sparse; keep inferred ∩ declared.
            catalog.upsert_model(
                connection_id=connection.connection_id,
                model_id=model_id,
                capabilities=capabilities,
                metadata={
                    "source": "qwen_declared_capability_seed",
                    "seeded_for": capability,
                },
                pricing=None,
            )
            if model_id not in seeded:
                seeded.append(model_id)
    session.flush()
    return tuple(seeded)


def materialize_qwen_runtime_defaults(
    session: Session,
) -> QwenRuntimeDefaultsReport:
    """Configure missing Qwen runtime defaults from connected model catalog rows."""

    # Ensure rerank/embedding catalog rows exist before looking up candidates.
    # OpenAI-compatible /models often omits these service models.
    for connection in session.scalars(select(ProviderConnection)):
        if connection.provider == "qwen":
            ensure_qwen_declared_capability_models(session, connection)

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
    """Return whether a Qwen base URL can serve native sparse embeddings.

    Accepts either the full DashScope text-embedding service URL or the API
    root (``…/api/v1``), which the embedding client expands to the service path.
    OpenAI-compatible chat gateways (Token Plan ``compatible-mode``, bare
    ``…/v1``) cannot serve sparse embeddings.
    """

    if base_url is None:
        return False
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        return False
    if "/compatible-mode/" in normalized:
        return False
    if "/services/embeddings/text-embedding" in normalized:
        return True
    if normalized.endswith("/api/v1"):
        return True
    if normalized.endswith("/v1"):
        return False
    return False


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
