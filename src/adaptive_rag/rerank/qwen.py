"""Qwen rerank provider and HTTP client."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

import httpx

from adaptive_rag.provider_usage import (
    ProviderBudgetExceededError,
    ProviderBudgetGuard,
    ProviderPriceCatalog,
    ProviderUsageTracker,
    build_failure_record,
    build_success_record,
    record_with_budget,
)
from adaptive_rag.rerank.providers import (
    RerankProviderError,
    RerankRequest,
    RerankResult,
    RerankScore,
)

_DEFAULT_RERANK_INSTRUCT = (
    "Given a web search query, retrieve relevant passages that answer the query."
)


class QwenRerankProviderError(RerankProviderError):
    """Error estable para respuestas del provider Qwen rerank."""


class QwenRerankClient(Protocol):
    """Cliente inyectable para rerank Qwen."""

    def rerank(
        self,
        *,
        model: str,
        request: RerankRequest,
    ) -> RerankResult:
        """Ejecuta rerank con el modelo indicado."""


@dataclass(slots=True)
class QwenRerankProvider:
    """Provider Qwen rerank con cliente inyectable y validacion de contrato."""

    model_name: str
    client: QwenRerankClient
    provider_name: str = "qwen"

    def rerank(self, request: RerankRequest) -> RerankResult:
        result = self.client.rerank(model=self.model_name, request=request)
        _validate_qwen_result(result, request=request, model_name=self.model_name)
        return result


@dataclass(frozen=True, slots=True)
class QwenHTTPRerankClient:
    """Cliente HTTP pequeno para Qwen qwen3-rerank compatible API."""

    api_key: str = field(repr=False)
    base_url: str
    timeout_seconds: float
    max_retries: int
    transport: httpx.BaseTransport | None = None
    usage_tracker: ProviderUsageTracker | None = None
    provider_name: str = "qwen"
    price_catalog: ProviderPriceCatalog = ProviderPriceCatalog()
    budget_guard: ProviderBudgetGuard | None = None
    instruct: str = _DEFAULT_RERANK_INSTRUCT

    def rerank(
        self,
        *,
        model: str,
        request: RerankRequest,
    ) -> RerankResult:
        endpoint = _rerank_endpoint(self.base_url)
        payload = _rerank_payload(
            model=model,
            request=request,
            instruct=self.instruct,
            use_input_object=_uses_dashscope_service_payload(endpoint),
        )
        started = perf_counter()
        try:
            response_data, request_id = self._post(
                endpoint=endpoint,
                payload=payload,
            )
            result = _parse_rerank_result(
                response_data,
                model=model,
                request=request,
                request_id=request_id,
            )
            record = build_success_record(
                provider=self.provider_name,
                model=model,
                operation="rerank",
                duration_ms=_elapsed_ms(started),
                response_data=response_data,
                price_catalog=self.price_catalog,
                request_id=request_id,
                input_count=len(request.candidates),
            )
            record_with_budget(
                record=record,
                tracker=self.usage_tracker,
                budget_guard=self.budget_guard,
            )
            return result
        except Exception as exc:
            if not isinstance(exc, ProviderBudgetExceededError):
                self._record_failure(
                    model=model,
                    duration_ms=_elapsed_ms(started),
                    error=exc,
                    input_count=len(request.candidates),
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
                    raise QwenRerankProviderError(
                        f"qwen rerank request failed with status {response.status_code}"
                    )
                data = response.json()
                if not isinstance(data, dict):
                    raise QwenRerankProviderError(
                        "qwen rerank response must be a JSON object"
                    )
                return data, _request_id(response, data)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt < attempts - 1:
                    continue
                break

        raise QwenRerankProviderError(
            "qwen rerank request failed before receiving a response"
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
                provider=self.provider_name,
                model=model,
                operation="rerank",
                duration_ms=duration_ms,
                error=error,
                input_count=input_count,
            )
        )


def _validate_qwen_result(
    result: RerankResult,
    *,
    request: RerankRequest,
    model_name: str,
) -> None:
    if result.provider_name != "qwen":
        raise QwenRerankProviderError("qwen rerank result provider mismatch")
    if result.model_name != model_name:
        raise QwenRerankProviderError("qwen rerank result model mismatch")
    if len(result.scores) > request.top_k:
        raise QwenRerankProviderError("qwen rerank returned too many scores")
    candidate_ids = {candidate.candidate_id for candidate in request.candidates}
    for score in result.scores:
        if score.candidate_id not in candidate_ids:
            raise QwenRerankProviderError("qwen rerank returned unknown candidate")


def _rerank_payload(
    *,
    model: str,
    request: RerankRequest,
    instruct: str,
    use_input_object: bool,
) -> dict[str, Any]:
    documents = [candidate.text for candidate in request.candidates]
    if use_input_object:
        return {
            "model": model,
            "input": {
                "query": request.query,
                "documents": documents,
            },
            "parameters": {
                "top_n": request.top_k,
                "instruct": instruct,
            },
        }

    return {
        "model": model,
        "documents": documents,
        "query": request.query,
        "top_n": request.top_k,
        "instruct": instruct,
    }


def _rerank_endpoint(base_url: str) -> str:
    value = base_url.rstrip("/")
    if value.endswith("/reranks") or value.endswith("/text-rerank"):
        return value
    if value.endswith("/compatible-mode/v1"):
        value = f"{value.removesuffix('/compatible-mode/v1')}/api/v1"
    if value.endswith("/api/v1"):
        return f"{value}/services/rerank/text-rerank/text-rerank"
    return f"{value}/reranks"


def _uses_dashscope_service_payload(endpoint: str) -> bool:
    return "/services/rerank/text-rerank/" in endpoint


def _parse_rerank_result(
    response_data: dict[str, Any],
    *,
    model: str,
    request: RerankRequest,
    request_id: str | None,
) -> RerankResult:
    output = response_data.get("output")
    if not isinstance(output, dict) or not isinstance(output.get("results"), list):
        raise QwenRerankProviderError("qwen rerank response missing output.results")

    scores = tuple(
        _score_from_item(
            item,
            request=request,
            rerank_rank=rerank_rank,
            request_id=request_id,
        )
        for rerank_rank, item in enumerate(output["results"], start=1)
    )
    return RerankResult(
        provider_name="qwen",
        model_name=model,
        scores=scores,
    )


def _score_from_item(
    item: object,
    *,
    request: RerankRequest,
    rerank_rank: int,
    request_id: str | None,
) -> RerankScore:
    if not isinstance(item, dict):
        raise QwenRerankProviderError("qwen rerank result item must be an object")
    index = _item_index(item.get("index"), candidate_count=len(request.candidates))
    score = _item_score(item.get("relevance_score"))
    candidate = request.candidates[index]
    metadata: dict[str, object] = {}
    if request_id is not None:
        metadata["request_id"] = request_id
    return RerankScore(
        candidate_id=candidate.candidate_id,
        score=score,
        original_rank=index + 1,
        rerank_rank=rerank_rank,
        metadata=metadata,
    )


def _item_index(value: object, *, candidate_count: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise QwenRerankProviderError("qwen rerank result index must be an integer")
    if value < 0 or value >= candidate_count:
        raise QwenRerankProviderError("qwen rerank returned unknown candidate index")
    return value


def _item_score(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise QwenRerankProviderError("qwen rerank relevance_score must be numeric")
    return float(value)


def _request_id(response: httpx.Response, response_data: dict[str, Any]) -> str | None:
    for header_name in ("x-request-id", "x-acs-request-id", "request-id"):
        value = response.headers.get(header_name)
        if value is not None:
            return str(value)
    request_id = response_data.get("request_id")
    return str(request_id) if request_id is not None else None


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))
