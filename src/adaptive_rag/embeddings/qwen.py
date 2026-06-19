"""Provider de embeddings Qwen/DashScope para runtime live opt-in."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol

import httpx

from adaptive_rag.db.models import EMBEDDING_DIMENSIONS
from adaptive_rag.provider_usage import (
    ProviderBudgetExceededError,
    ProviderBudgetGuard,
    ProviderPriceCatalog,
    ProviderUsageTracker,
    build_failure_record,
    build_success_record,
    record_with_budget,
)


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
    usage_tracker: ProviderUsageTracker | None = None
    price_catalog: ProviderPriceCatalog = ProviderPriceCatalog()
    budget_guard: ProviderBudgetGuard | None = None

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
        started = perf_counter()
        try:
            response_data, request_id = self._post(endpoint=endpoint, payload=payload)
            embeddings = _extract_embeddings(response_data)
            record = build_success_record(
                provider="qwen",
                model=model,
                operation="embedding",
                duration_ms=_elapsed_ms(started),
                response_data=response_data,
                price_catalog=self.price_catalog,
                request_id=request_id,
                input_count=len(texts),
            )
            record_with_budget(
                record=record,
                tracker=self.usage_tracker,
                budget_guard=self.budget_guard,
            )
            return embeddings
        except Exception as exc:
            if not _is_budget_error(exc):
                self._record_failure(
                    model=model,
                    duration_ms=_elapsed_ms(started),
                    error=exc,
                    input_count=len(texts),
                )
            raise

    def _post(
        self,
        *,
        endpoint: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], str | None]:
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
                return data, _response_request_id(response)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt < attempts - 1:
                    continue
                break

        raise QwenEmbeddingProviderError(
            "qwen embedding request failed before receiving a response"
        ) from last_error

    def _record_failure(
        self,
        *,
        model: str,
        duration_ms: int,
        error: Exception,
        input_count: int,
    ) -> None:
        if self.usage_tracker is None:
            return
        self.usage_tracker.record(
            build_failure_record(
                provider="qwen",
                model=model,
                operation="embedding",
                duration_ms=duration_ms,
                error=error,
                input_count=input_count,
            )
        )


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


def _response_request_id(response: httpx.Response) -> str | None:
    for header_name in ("x-request-id", "x-acs-request-id", "request-id"):
        value = response.headers.get(header_name)
        if value is not None:
            return str(value)
    return None


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))


def _is_budget_error(exc: Exception) -> bool:
    return isinstance(exc, ProviderBudgetExceededError)
