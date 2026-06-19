"""Provider de embeddings Qwen/DashScope para runtime live opt-in."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from adaptive_rag.db.models import EMBEDDING_DIMENSIONS


class QwenEmbeddingProviderError(ValueError):
    """Error estable para llamadas de embeddings Qwen."""


class QwenEmbeddingClient(Protocol):
    def embed_texts(
        self,
        *,
        model: str,
        texts: list[str],
        dimensions: int,
    ) -> list[list[float]]:
        """Genera embeddings para textos con el modelo indicado."""


@dataclass(slots=True)
class QwenDenseEmbeddingProvider:
    """Implementa DenseEmbeddingProvider usando un cliente Qwen inyectable."""

    model_name: str
    client: QwenEmbeddingClient
    provider_name: str = "qwen"
    dimensions: int = EMBEDDING_DIMENSIONS

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings = self.client.embed_texts(
            model=self.model_name,
            texts=texts,
            dimensions=self.dimensions,
        )
        if len(embeddings) != len(texts):
            raise QwenEmbeddingProviderError(
                "qwen embedding provider returned wrong count: "
                f"expected {len(texts)}, got {len(embeddings)}"
            )
        for embedding in embeddings:
            if len(embedding) != self.dimensions:
                raise QwenEmbeddingProviderError(
                    "qwen embedding dimension mismatch: "
                    f"expected {self.dimensions}, got {len(embedding)}"
                )
        return embeddings


@dataclass(frozen=True, slots=True)
class QwenHTTPEmbeddingClient:
    """Cliente HTTP pequeno para endpoints Qwen/DashScope de embeddings."""

    api_key: str
    base_url: str
    timeout_seconds: float
    max_retries: int
    transport: httpx.BaseTransport | None = None

    def embed_texts(
        self,
        *,
        model: str,
        texts: list[str],
        dimensions: int,
    ) -> list[list[float]]:
        endpoint, payload = _embedding_request(
            base_url=self.base_url,
            model=model,
            texts=texts,
            dimensions=dimensions,
        )
        response_data = self._post(endpoint=endpoint, payload=payload)
        return _extract_embeddings(response_data)

    def _post(self, *, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        attempts = max(0, self.max_retries) + 1
        for attempt in range(attempts):
            try:
                with httpx.Client(
                    timeout=self.timeout_seconds,
                    transport=self.transport,
                ) as client:
                    response = client.post(
                        endpoint,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                if response.status_code >= 500 and attempt < attempts - 1:
                    continue
                if response.status_code >= 400:
                    raise QwenEmbeddingProviderError(
                        "qwen embedding request failed with status "
                        f"{response.status_code}"
                    )
                data = response.json()
                if not isinstance(data, dict):
                    raise QwenEmbeddingProviderError(
                        "qwen embedding response must be a JSON object"
                    )
                return data
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt < attempts - 1:
                    continue
                break

        raise QwenEmbeddingProviderError(
            "qwen embedding request failed before receiving a response"
        ) from last_error


def _embedding_request(
    *,
    base_url: str,
    model: str,
    texts: list[str],
    dimensions: int,
) -> tuple[str, dict[str, Any]]:
    if _is_openai_compatible_base(base_url):
        return (
            _embedding_endpoint(base_url),
            {
                "model": model,
                "input": texts,
                "dimensions": dimensions,
            },
        )

    return (
        _embedding_endpoint(base_url),
        {
            "model": model,
            "input": {"texts": texts},
            "parameters": {"dimension": dimensions},
        },
    )


def _is_openai_compatible_base(base_url: str) -> bool:
    value = base_url.rstrip("/")
    return value.endswith("/v1") or "/compatible-mode/" in value


def _embedding_endpoint(base_url: str) -> str:
    value = base_url.rstrip("/")
    if value.endswith("/embeddings") or value.endswith("/text-embedding"):
        return value
    return f"{value}/embeddings"


def _extract_embeddings(response_data: dict[str, Any]) -> list[list[float]]:
    if isinstance(response_data.get("data"), list):
        items = sorted(
            response_data["data"],
            key=lambda item: item.get("index", 0) if isinstance(item, dict) else 0,
        )
        return [_embedding_from_item(item) for item in items]

    output = response_data.get("output")
    if isinstance(output, dict) and isinstance(output.get("embeddings"), list):
        items = sorted(
            output["embeddings"],
            key=lambda item: (
                item.get("text_index", 0) if isinstance(item, dict) else 0
            ),
        )
        return [_embedding_from_item(item) for item in items]

    raise QwenEmbeddingProviderError(
        "qwen embedding response does not contain embeddings"
    )


def _embedding_from_item(item: object) -> list[float]:
    if not isinstance(item, dict) or not isinstance(item.get("embedding"), list):
        raise QwenEmbeddingProviderError(
            "qwen embedding response item is missing embedding"
        )
    return [float(value) for value in item["embedding"]]
