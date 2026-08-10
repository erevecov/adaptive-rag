"""Published USD list prices for Alibaba Cloud Model Studio (Qwen/DashScope).

Updates ``provider_model_catalog.pricing_json`` for real ``qwen`` connections.

Source of truth
---------------
- Official page: https://www.alibabacloud.com/help/en/model-studio/model-pricing
- Region/scope used here: **Singapore / International** standard list prices
  (pay-as-you-go). Limited-time promotions and night/day discounts are ignored.
- Token Plan prepaid packages are *not* modeled; rates below are list prices.
- OpenAI-compatible ``GET …/models`` does **not** return pricing fields (verified
  against Bailian Token Plan). Native ``GET /api/v1/models`` requires a Model
  Studio key that accepts that host; Token Plan keys return InvalidApiKey.
  Until a reliable pricing API is available, this static map is the source.

When a ``model_id`` has no published entry in this catalog, pricing is left
unchanged (lookup returns ``None``; the sync job skips). Never invent prices.

``pricing_json`` shape (aligned with API/frontend expectations)::

    {
      # Token models (chat / embed / rerank):
      "input_per_million_tokens_usd": 0.4,
      "output_per_million_tokens_usd": 1.2,   # chat only; omit for embed/rerank
      # Image models (Wan):
      "usd_per_image": 0.03,
      # Character-billed TTS:
      "input_per_10k_characters_usd": 0.2,
      "currency": "USD",
      "source": "alibaba_model_studio_singapore_list",
      "source_url": "https://www.alibabacloud.com/help/en/model-studio/model-pricing",
      "as_of": "2026-08-10",
      "deployment_scope": "International",
      # optional:
      "output_thinking_per_million_tokens_usd": 4.0,
      "tiers": [...],
      "notes": "..."
    }
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy.orm import Session

from adaptive_rag.db.repositories import (
    ProviderConnectionRepository,
    ProviderModelCatalogRepository,
)

logger = logging.getLogger(__name__)

PRICING_SOURCE_URL = "https://www.alibabacloud.com/help/en/model-studio/model-pricing"
PRICING_AS_OF = "2026-08-10"
PRICING_SOURCE = "alibaba_model_studio_singapore_list"
PRICING_DEPLOYMENT_SCOPE = "International"

# Provider value for Alibaba/DashScope/Bailian connections in this product.
QWEN_PROVIDER = "qwen"


def _base_meta() -> dict[str, Any]:
    return {
        "currency": "USD",
        "source": PRICING_SOURCE,
        "source_url": PRICING_SOURCE_URL,
        "as_of": PRICING_AS_OF,
        "deployment_scope": PRICING_DEPLOYMENT_SCOPE,
    }


def chat_pricing(
    input_per_million: float,
    output_per_million: float,
    *,
    output_thinking_per_million: float | None = None,
    tiers: list[dict[str, Any]] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build chat/completion pricing_json (input + output per 1M tokens USD)."""

    payload: dict[str, Any] = {
        **_base_meta(),
        "input_per_million_tokens_usd": input_per_million,
        "output_per_million_tokens_usd": output_per_million,
    }
    if output_thinking_per_million is not None:
        payload["output_thinking_per_million_tokens_usd"] = (
            output_thinking_per_million
        )
    if tiers is not None:
        payload["tiers"] = tiers
    if notes is not None:
        payload["notes"] = notes
    return payload


def embedding_pricing(
    input_per_million: float,
    *,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build embedding pricing_json (input only; output free)."""

    payload: dict[str, Any] = {
        **_base_meta(),
        "input_per_million_tokens_usd": input_per_million,
        "notes": notes or "Billed by input tokens; output free.",
    }
    return payload


def rerank_pricing(
    input_per_million: float,
    *,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build rerank pricing_json (input only; output free)."""

    payload: dict[str, Any] = {
        **_base_meta(),
        "input_per_million_tokens_usd": input_per_million,
        "notes": notes or "Billed by input tokens; output free.",
    }
    return payload


def image_pricing(
    usd_per_image: float,
    *,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build image-generation pricing_json (pay per image)."""

    payload: dict[str, Any] = {
        **_base_meta(),
        "usd_per_image": usd_per_image,
        "billing_unit": "image",
        "notes": notes or "Billed per generated image.",
    }
    return payload


def character_pricing(
    usd_per_10k_characters: float,
    *,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build character-billed TTS pricing_json."""

    payload: dict[str, Any] = {
        **_base_meta(),
        "input_per_10k_characters_usd": usd_per_10k_characters,
        "billing_unit": "characters",
        "notes": notes or "Billed per 10,000 input characters; output free.",
    }
    return payload


def _tier(
    *,
    max_input_tokens: int,
    input_per_million: float,
    output_per_million: float,
    output_thinking_per_million: float | None = None,
) -> dict[str, Any]:
    tier: dict[str, Any] = {
        "max_input_tokens": max_input_tokens,
        "input_per_million_tokens_usd": input_per_million,
        "output_per_million_tokens_usd": output_per_million,
    }
    if output_thinking_per_million is not None:
        tier["output_thinking_per_million_tokens_usd"] = output_thinking_per_million
    return tier


# Singapore / International standard list prices (as_of PRICING_AS_OF).
# Primary input/output fields use the lowest common tier (typical RAG traffic).
_QWEN_MODEL_PRICING: dict[str, dict[str, Any]] = {
    # --- Chat aliases used by this product ---
    "qwen-plus": chat_pricing(
        0.4,
        1.2,
        output_thinking_per_million=4.0,
        tiers=[
            _tier(
                max_input_tokens=256_000,
                input_per_million=0.4,
                output_per_million=1.2,
                output_thinking_per_million=4.0,
            ),
            _tier(
                max_input_tokens=1_000_000,
                input_per_million=1.2,
                output_per_million=3.6,
                output_thinking_per_million=12.0,
            ),
        ],
        notes="Primary fields are 0–256K tier (non-thinking output).",
    ),
    "qwen-plus-latest": chat_pricing(
        0.4,
        1.2,
        output_thinking_per_million=4.0,
        notes="Alias pricing mirrors qwen-plus international list.",
    ),
    "qwen-plus-2025-12-01": chat_pricing(
        0.4, 1.2, output_thinking_per_million=4.0
    ),
    "qwen-plus-2025-09-11": chat_pricing(
        0.4, 1.2, output_thinking_per_million=4.0
    ),
    "qwen-plus-2025-07-28": chat_pricing(
        0.4, 1.2, output_thinking_per_million=4.0
    ),
    "qwen-plus-2025-07-14": chat_pricing(
        0.4, 1.2, output_thinking_per_million=4.0
    ),
    "qwen-max": chat_pricing(1.6, 6.4),
    "qwen-turbo": chat_pricing(0.05, 0.2, output_thinking_per_million=0.5),
    "qwen-flash": chat_pricing(
        0.05,
        0.4,
        tiers=[
            _tier(
                max_input_tokens=256_000,
                input_per_million=0.05,
                output_per_million=0.4,
            ),
            _tier(
                max_input_tokens=1_000_000,
                input_per_million=0.25,
                output_per_million=2.0,
            ),
        ],
        notes="Primary fields are 0–256K tier.",
    ),
    "qwen3.7-plus": chat_pricing(
        0.4,
        1.6,
        tiers=[
            _tier(
                max_input_tokens=256_000,
                input_per_million=0.4,
                output_per_million=1.6,
            ),
            _tier(
                max_input_tokens=1_000_000,
                input_per_million=1.2,
                output_per_million=4.8,
            ),
        ],
        notes=(
            "Primary fields are 0–256K list tier "
            "(matches ADAPTIVE_RAG_PROVIDER_CHAT_* defaults)."
        ),
    ),
    "qwen3.7-plus-2026-05-26": chat_pricing(0.4, 1.6),
    "qwen3.6-plus": chat_pricing(
        0.5,
        3.0,
        tiers=[
            _tier(
                max_input_tokens=256_000,
                input_per_million=0.5,
                output_per_million=3.0,
            ),
            _tier(
                max_input_tokens=1_000_000,
                input_per_million=2.0,
                output_per_million=6.0,
            ),
        ],
    ),
    "qwen3.6-plus-2026-04-02": chat_pricing(0.5, 3.0),
    "qwen3.5-plus": chat_pricing(
        0.4,
        2.4,
        tiers=[
            _tier(
                max_input_tokens=256_000,
                input_per_million=0.4,
                output_per_million=2.4,
            ),
            _tier(
                max_input_tokens=1_000_000,
                input_per_million=0.5,
                output_per_million=3.0,
            ),
        ],
    ),
    "qwen3.5-plus-2026-02-15": chat_pricing(0.4, 2.4),
    "qwen3.5-flash": chat_pricing(0.1, 0.4),
    "qwen3.5-flash-2026-02-23": chat_pricing(0.1, 0.4),
    "qwen3.6-flash": chat_pricing(
        0.25,
        1.5,
        tiers=[
            _tier(
                max_input_tokens=256_000,
                input_per_million=0.25,
                output_per_million=1.5,
            ),
            _tier(
                max_input_tokens=1_000_000,
                input_per_million=1.0,
                output_per_million=4.0,
            ),
        ],
    ),
    "qwen3.7-max": chat_pricing(
        2.5,
        7.5,
        notes="List price (promotional 50% off ignored).",
    ),
    "qwen3.7-max-2026-05-20": chat_pricing(2.5, 7.5),
    # Flagship listed on Model Studio international product pages (Aug 2026).
    "qwen3.8-max": chat_pricing(
        2.0,
        6.0,
        notes=(
            "International list from Model Studio product pricing "
            "($2 / $6 per 1M). Prefer model-pricing doc when a full tier table "
            "is published for this id."
        ),
    ),
    "qwen3.8-max-preview": chat_pricing(
        2.0,
        6.0,
        notes="Alias pricing mirrors qwen3.8-max international list.",
    ),
    "qwen3-max": chat_pricing(
        1.2,
        6.0,
        tiers=[
            _tier(
                max_input_tokens=32_000,
                input_per_million=1.2,
                output_per_million=6.0,
            ),
            _tier(
                max_input_tokens=128_000,
                input_per_million=2.4,
                output_per_million=12.0,
            ),
            _tier(
                max_input_tokens=256_000,
                input_per_million=3.0,
                output_per_million=15.0,
            ),
        ],
        notes="Primary fields are 0–32K tier.",
    ),
    "qwq-plus": chat_pricing(0.8, 2.4),
    # Vision chat (common in catalog sync)
    "qwen-vl-plus": chat_pricing(0.21, 0.63),
    "qwen-vl-max": chat_pricing(0.8, 3.2),
    "qwen3-vl-plus": chat_pricing(
        0.2,
        1.6,
        tiers=[
            _tier(
                max_input_tokens=32_000,
                input_per_million=0.2,
                output_per_million=1.6,
            ),
            _tier(
                max_input_tokens=128_000,
                input_per_million=0.3,
                output_per_million=2.4,
            ),
            _tier(
                max_input_tokens=256_000,
                input_per_million=0.6,
                output_per_million=4.8,
            ),
        ],
        notes="Primary fields are 0–32K tier.",
    ),
    "qwen3-vl-flash": chat_pricing(
        0.05,
        0.4,
        tiers=[
            _tier(
                max_input_tokens=32_000,
                input_per_million=0.05,
                output_per_million=0.4,
            ),
            _tier(
                max_input_tokens=128_000,
                input_per_million=0.075,
                output_per_million=0.6,
            ),
            _tier(
                max_input_tokens=256_000,
                input_per_million=0.12,
                output_per_million=0.96,
            ),
        ],
        notes="Primary fields are 0–32K tier.",
    ),
    # --- Third-party text (Model Studio Singapore list) ---
    "deepseek-v4-pro": chat_pricing(2.4, 4.8),
    "deepseek-v4-flash": chat_pricing(0.2, 0.4),
    # Catalog sometimes exposes dated flash builds; same list tier as flash.
    "deepseek-v4-flash-0731": chat_pricing(
        0.2,
        0.4,
        notes="Alias of deepseek-v4-flash Singapore list price.",
    ),
    "glm-5.2": chat_pricing(
        1.4,
        4.4,
        notes="Flat-rate international list (non-thinking and thinking).",
    ),
    # --- Image (Wan) — billed per image, not per 1M tokens ---
    "wan2.7-image": image_pricing(0.03),
    "wan2.7-image-pro": image_pricing(0.075),
    # --- Audio TTS — billed per 10k input characters ---
    "qwen-audio-3.0-tts-plus": character_pricing(0.2),
    "qwen-audio-3.0-tts-flash": character_pricing(0.15),
    # --- Embeddings ---
    "text-embedding-v4": embedding_pricing(0.07),
    "text-embedding-v3": embedding_pricing(0.07),
    # --- Rerank ---
    "qwen3-rerank": rerank_pricing(0.1),
}


def lookup_qwen_pricing(model_id: str) -> dict[str, Any] | None:
    """Return published pricing_json for a Qwen/DashScope model_id, or None.

    Exact match only after strip + lowercasing. Unknown ids return None so the
    sync job can skip without inventing prices.
    """

    normalized = model_id.strip().lower()
    if not normalized:
        return None
    pricing = _QWEN_MODEL_PRICING.get(normalized)
    if pricing is None:
        return None
    return dict(pricing)


def known_qwen_pricing_model_ids() -> frozenset[str]:
    """Model ids covered by the static Alibaba international list catalog."""

    return frozenset(_QWEN_MODEL_PRICING)


@dataclass(frozen=True, slots=True)
class PricingSyncReport:
    """Safe summary of a pricing sync run (no secrets)."""

    provider: str
    connections_seen: int
    models_seen: int
    updated: int
    unchanged: int
    skipped_unknown: int
    skipped_non_target_provider: int
    dry_run: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def sync_provider_model_pricing(
    session: Session,
    *,
    provider: str = QWEN_PROVIDER,
    dry_run: bool = False,
) -> PricingSyncReport:
    """Update ``pricing_json`` for catalog models of real provider connections.

    Only connections whose ``provider`` matches ``provider`` (default ``qwen``)
    are considered. Fake / local_openai_compatible connections are counted as
    skipped_non_target_provider. Models without a published price are skipped
    (``pricing_json`` left as-is). Idempotent: identical pricing is unchanged.
    """

    target = provider.strip().lower()
    if target != QWEN_PROVIDER:
        # Only Alibaba/Qwen pricing is implemented; do not invent other catalogs.
        raise ValueError(
            f"unsupported pricing provider: {provider!r} "
            f"(only {QWEN_PROVIDER!r} is supported)"
        )

    connections = ProviderConnectionRepository(session).list_connections()
    catalog = ProviderModelCatalogRepository(session)

    connections_seen = 0
    models_seen = 0
    updated = 0
    unchanged = 0
    skipped_unknown = 0
    skipped_non_target = 0

    for connection in connections:
        if connection.provider != target:
            skipped_non_target += 1
            continue
        connections_seen += 1
        models = catalog.list_models(connection_id=connection.connection_id)
        for model in models:
            models_seen += 1
            pricing = lookup_qwen_pricing(model.model_id)
            if pricing is None:
                skipped_unknown += 1
                logger.info(
                    "provider_pricing_skip_unknown",
                    extra={
                        "connection_id": connection.connection_id,
                        "model_id": model.model_id,
                        "provider": connection.provider,
                    },
                )
                continue
            if _pricing_equal(model.pricing_json, pricing):
                unchanged += 1
                continue
            if not dry_run:
                catalog.update_model_pricing(
                    connection_id=connection.connection_id,
                    model_id=model.model_id,
                    pricing=pricing,
                )
            updated += 1
            logger.info(
                "provider_pricing_updated",
                extra={
                    "connection_id": connection.connection_id,
                    "model_id": model.model_id,
                    "provider": connection.provider,
                    "dry_run": dry_run,
                    "as_of": PRICING_AS_OF,
                },
            )

    return PricingSyncReport(
        provider=target,
        connections_seen=connections_seen,
        models_seen=models_seen,
        updated=updated,
        unchanged=unchanged,
        skipped_unknown=skipped_unknown,
        skipped_non_target_provider=skipped_non_target,
        dry_run=dry_run,
    )


def _pricing_equal(
    existing: Mapping[str, Any] | None,
    candidate: Mapping[str, Any],
) -> bool:
    if existing is None:
        return False
    return dict(existing) == dict(candidate)
