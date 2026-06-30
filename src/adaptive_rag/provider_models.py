"""Provider model discovery helpers for runtime settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from adaptive_rag.db.models import (
    PROVIDER_CONNECTION_CAPABILITY_VALUES,
    ProviderConnection,
)
from adaptive_rag.runtime.qwen_defaults import infer_qwen_model_capabilities


@dataclass(frozen=True, slots=True)
class ProviderModelInfo:
    """Safe model metadata returned by provider model discovery."""

    model_id: str
    capabilities: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None
    pricing: dict[str, Any] | None = None


class ProviderModelLister(Protocol):
    def list_models(
        self,
        connection: ProviderConnection,
        *,
        api_key: str | None,
    ) -> list[ProviderModelInfo]:
        """List provider model IDs for a configured connection."""


@dataclass(frozen=True, slots=True)
class HTTPProviderModelLister:
    """Lists provider models from OpenAI-compatible model endpoints."""

    timeout_seconds: float
    transport: httpx.BaseTransport | None = None

    def list_models(
        self,
        connection: ProviderConnection,
        *,
        api_key: str | None,
    ) -> list[ProviderModelInfo]:
        if connection.provider == "fake":
            return _fake_models(connection)
        if connection.provider not in {"qwen", "local_openai_compatible"}:
            raise ValueError(
                f"unsupported provider model listing: {connection.provider}"
            )
        if not connection.base_url:
            raise ValueError("provider model listing requires base_url")

        with httpx.Client(
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            response = client.get(
                _models_endpoint(connection.base_url),
                headers=_headers(api_key),
            )
        if response.status_code >= 400:
            raise ValueError(
                f"provider model list failed with status {response.status_code}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise ValueError("provider model response invalid JSON") from exc
        items = _model_items(data)
        if items is None:
            raise ValueError("provider model response missing data")
        return [
            _model_from_item(item, provider=connection.provider)
            for item in items
        ]


def _headers(api_key: str | None) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _models_endpoint(base_url: str) -> str:
    value = base_url.rstrip("/")
    if value.endswith("/models"):
        return value
    return f"{value}/models"


def _model_items(data: object) -> list[object] | None:
    if not isinstance(data, dict):
        return None
    items = data.get("data")
    if isinstance(items, list):
        return items
    output = data.get("output")
    if isinstance(output, dict):
        output_items = output.get("data")
        if isinstance(output_items, list):
            return output_items
    return None


def _model_from_item(item: object, *, provider: str) -> ProviderModelInfo:
    if not isinstance(item, dict):
        raise ValueError("provider model item must be an object")
    model_id = item.get("id")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("provider model item missing id")
    normalized_model_id = model_id.strip()
    capabilities = _capabilities_from_item(item)
    if not capabilities and provider == "qwen":
        capabilities = infer_qwen_model_capabilities(normalized_model_id)
    pricing = _pricing_from_item(item)
    return ProviderModelInfo(
        model_id=normalized_model_id,
        capabilities=capabilities,
        metadata=dict(item),
        pricing=pricing,
    )


def _capabilities_from_item(item: dict[str, Any]) -> tuple[str, ...]:
    value = item.get("capabilities")
    if not isinstance(value, list):
        return ()
    requested = set()
    for capability in value:
        if not isinstance(capability, str):
            continue
        normalized = capability.strip()
        if normalized in PROVIDER_CONNECTION_CAPABILITY_VALUES:
            requested.add(normalized)
    return tuple(
        capability
        for capability in PROVIDER_CONNECTION_CAPABILITY_VALUES
        if capability in requested
    )


def _pricing_from_item(item: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("pricing", "price"):
        value = item.get(key)
        if isinstance(value, dict):
            return dict(value)
    return None


def _fake_models(connection: ProviderConnection) -> list[ProviderModelInfo]:
    by_capability = {
        "chat": "retrieval-grounded-local-v1",
        "dense_embedding": "fake-embedding-v1",
        "sparse_embedding": "fake-sparse-embedding-v1",
        "rerank": "fake-rerank-v1",
        "contextualization": "deterministic-context-v1",
    }
    models: dict[str, list[str]] = {}
    for capability in connection.capabilities_json:
        model_id = by_capability.get(capability)
        if model_id is None:
            continue
        models.setdefault(model_id, []).append(capability)
    return [
        ProviderModelInfo(
            model_id=model_id,
            capabilities=tuple(capabilities),
            metadata={"source": "fake"},
        )
        for model_id, capabilities in models.items()
    ]
