"""Qwen rerank provider contract without live HTTP implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from adaptive_rag.rerank.providers import (
    RerankProviderError,
    RerankRequest,
    RerankResult,
)


class QwenRerankProviderError(RerankProviderError):
    """Error estable para respuestas del provider Qwen rerank."""


class QwenRerankClient(Protocol):
    """Cliente inyectable para una implementacion Qwen live posterior."""

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

