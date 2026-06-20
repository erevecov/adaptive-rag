"""Provider-neutral rerank contracts and deterministic fake implementation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol


class RerankProviderError(ValueError):
    """Error estable para requests o respuestas de rerank invalidas."""


@dataclass(frozen=True, slots=True)
class RerankCandidate:
    """Documento/candidato ya filtrado que puede ser reordenado por rerank."""

    candidate_id: str
    text: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise RerankProviderError("rerank candidate id is required")
        if not self.text.strip():
            raise RerankProviderError("rerank candidate text is required")


@dataclass(frozen=True, slots=True)
class RerankRequest:
    """Solicitud provider-neutral para reordenar candidatos de retrieval."""

    query: str
    candidates: tuple[RerankCandidate, ...]
    top_k: int

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise RerankProviderError("rerank query must not be empty")
        if not self.candidates:
            raise RerankProviderError("rerank candidates must not be empty")
        if self.top_k <= 0:
            raise RerankProviderError("rerank top_k must be positive")
        if self.top_k > len(self.candidates):
            raise RerankProviderError(
                "rerank top_k must be less than or equal to candidate count"
            )
        candidate_ids = [candidate.candidate_id for candidate in self.candidates]
        if len(set(candidate_ids)) != len(candidate_ids):
            raise RerankProviderError("rerank candidate ids must be unique")


@dataclass(frozen=True, slots=True)
class RerankScore:
    """Score normalizado para un candidato reordenado."""

    candidate_id: str
    score: float
    original_rank: int
    rerank_rank: int
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RerankResult:
    """Resultado serializable de una llamada de rerank."""

    provider_name: str
    model_name: str
    scores: tuple[RerankScore, ...]


class RerankProvider(Protocol):
    """Contrato minimo para providers de rerank."""

    provider_name: str
    model_name: str

    def rerank(self, request: RerankRequest) -> RerankResult:
        """Reordena candidatos de una solicitud ya validada."""


class FakeRerankProvider:
    """Reranker determinista y sin red para tests, evals offline y defaults."""

    provider_name = "fake"
    model_name = "fake-rerank-v1"

    def __init__(self) -> None:
        self._requests: list[RerankRequest] = []

    @property
    def requests(self) -> tuple[RerankRequest, ...]:
        return tuple(self._requests)

    def rerank(self, request: RerankRequest) -> RerankResult:
        self._requests.append(request)
        query_terms = _token_set(request.query)
        scored = [
            (
                _lexical_overlap_score(query_terms=query_terms, text=candidate.text),
                original_rank,
                candidate,
            )
            for original_rank, candidate in enumerate(request.candidates, start=1)
        ]
        scored.sort(key=lambda item: (-item[0], item[1]))
        scores = tuple(
            RerankScore(
                candidate_id=candidate.candidate_id,
                score=score,
                original_rank=original_rank,
                rerank_rank=rerank_rank,
            )
            for rerank_rank, (score, original_rank, candidate) in enumerate(
                scored[: request.top_k],
                start=1,
            )
        )
        return RerankResult(
            provider_name=self.provider_name,
            model_name=self.model_name,
            scores=scores,
        )


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _lexical_overlap_score(*, query_terms: set[str], text: str) -> float:
    if not query_terms:
        return 0.0
    candidate_terms = _token_set(text)
    return len(query_terms & candidate_terms) / len(query_terms)
