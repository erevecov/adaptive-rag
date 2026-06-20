"""Servicio compartido para la superficie de retrieval M4."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.db.models import EMBEDDING_DIMENSIONS
from adaptive_rag.embeddings import DenseEmbeddingProvider
from adaptive_rag.provider_usage import ProviderBudgetExceededError
from adaptive_rag.rerank import (
    RerankCandidate,
    RerankProvider,
    RerankProviderError,
    RerankRequest,
    RerankResult,
    RerankScore,
)
from adaptive_rag.retrieval.dense import (
    DenseRetrievalCitation,
    DenseRetrievalError,
    DenseRetrievalFilters,
    DenseRetrievalResult,
    DenseRetriever,
)


class RetrievalServiceError(ValueError):
    """Error no retryable de la superficie compartida de retrieval."""


@dataclass(frozen=True, slots=True)
class RetrievalMetadataFilter:
    """Filtros externos soportados por la superficie compartida."""

    source_id: UUID | None = None
    document_id: UUID | None = None
    source_type: str | None = None
    tags: tuple[str, ...] = ()
    source_created_at_from: datetime | None = None
    source_created_at_to: datetime | None = None
    document_created_at_from: datetime | None = None
    document_created_at_to: datetime | None = None


@dataclass(frozen=True, slots=True)
class RetrievalRerankOptions:
    """Opciones explicitas para reordenar candidatos dense ya filtrados."""

    candidate_limit: int


@dataclass(frozen=True, slots=True)
class RetrievalSearchRequest:
    """Solicitud interna de retrieval sobre query text."""

    project_id: UUID
    query: str
    limit: int = 10
    metadata_filter: RetrievalMetadataFilter | None = None
    rerank: RetrievalRerankOptions | None = None


@dataclass(frozen=True, slots=True)
class RetrievalSearchResult:
    """Resultado de retrieval serializable por futuras superficies API/CLI."""

    chunk_id: UUID
    distance: float
    score: float
    citation: DenseRetrievalCitation
    embedding_metadata: dict[str, Any] | None
    rerank_metadata: dict[str, Any] | None = None


class RetrievalService:
    """Genera query embeddings y delega retrieval exacto al baseline M3."""

    def __init__(
        self,
        session: Session,
        *,
        provider: DenseEmbeddingProvider,
        reranker: RerankProvider | None = None,
    ) -> None:
        self._provider = provider
        self._reranker = reranker
        self._retriever = DenseRetriever(session)

    def search(self, request: RetrievalSearchRequest) -> list[RetrievalSearchResult]:
        query = _validate_query(request.query)
        if request.limit <= 0:
            raise RetrievalServiceError("limit must be positive")
        rerank_options = _validate_rerank_options(
            request.rerank,
            limit=request.limit,
            reranker=self._reranker,
        )

        filters = _to_dense_filters(request.metadata_filter)
        query_embedding = self._embed_query(query)
        dense_limit = (
            rerank_options.candidate_limit
            if rerank_options is not None
            else request.limit
        )

        try:
            results = self._retriever.search(
                project_id=request.project_id,
                query_embedding=query_embedding,
                limit=dense_limit,
                filters=filters,
            )
        except DenseRetrievalError as exc:
            raise RetrievalServiceError(str(exc)) from exc

        search_results = [_to_search_result(result) for result in results]
        if rerank_options is None or not search_results:
            return search_results
        return self._rerank_results(
            query=query,
            results=search_results,
            limit=request.limit,
            options=rerank_options,
        )

    def _embed_query(self, query: str) -> Sequence[float]:
        if self._provider.dimensions != EMBEDDING_DIMENSIONS:
            raise RetrievalServiceError(
                "query embedding dimension mismatch: "
                f"expected {EMBEDDING_DIMENSIONS}, got {self._provider.dimensions}"
            )

        embeddings = self._provider.embed_texts([query])
        if len(embeddings) != 1:
            raise RetrievalServiceError("query embedding provider returned wrong count")
        return embeddings[0]

    def _rerank_results(
        self,
        *,
        query: str,
        results: list[RetrievalSearchResult],
        limit: int,
        options: RetrievalRerankOptions,
    ) -> list[RetrievalSearchResult]:
        if self._reranker is None:
            raise RetrievalServiceError(
                "rerank provider is required when rerank is enabled"
            )

        top_k = min(limit, len(results))
        candidates = tuple(
            RerankCandidate(
                candidate_id=str(result.chunk_id),
                text=result.citation.snippet,
                metadata={
                    "chunk_id": str(result.chunk_id),
                    "dense_rank": dense_rank,
                },
            )
            for dense_rank, result in enumerate(results, start=1)
        )
        try:
            request = RerankRequest(query=query, candidates=candidates, top_k=top_k)
            rerank_result = self._reranker.rerank(request)
        except (ProviderBudgetExceededError, RerankProviderError) as exc:
            raise RetrievalServiceError(f"rerank failed: {exc}") from exc

        return _apply_rerank_result(
            results=results,
            rerank_result=rerank_result,
            candidate_limit=options.candidate_limit,
        )


def _validate_query(query: str) -> str:
    value = query.strip()
    if not value:
        raise RetrievalServiceError("query must not be empty")
    return value


def _validate_rerank_options(
    rerank_options: RetrievalRerankOptions | None,
    *,
    limit: int,
    reranker: RerankProvider | None,
) -> RetrievalRerankOptions | None:
    if rerank_options is None:
        return None
    if rerank_options.candidate_limit <= 0:
        raise RetrievalServiceError("rerank candidate_limit must be positive")
    if rerank_options.candidate_limit < limit:
        raise RetrievalServiceError(
            "rerank candidate_limit must be greater than or equal to limit"
        )
    if reranker is None:
        raise RetrievalServiceError(
            "rerank provider is required when rerank is enabled"
        )
    return rerank_options


def _to_search_result(result: DenseRetrievalResult) -> RetrievalSearchResult:
    return RetrievalSearchResult(
        chunk_id=result.chunk_id,
        distance=result.distance,
        score=result.score,
        citation=result.citation,
        embedding_metadata=(
            dict(result.embedding_metadata)
            if result.embedding_metadata is not None
            else None
        ),
    )


def _apply_rerank_result(
    *,
    results: list[RetrievalSearchResult],
    rerank_result: RerankResult,
    candidate_limit: int,
) -> list[RetrievalSearchResult]:
    by_candidate_id = {str(result.chunk_id): result for result in results}
    dense_rank_by_candidate_id = {
        str(result.chunk_id): dense_rank
        for dense_rank, result in enumerate(results, start=1)
    }
    seen_candidate_ids: set[str] = set()
    reranked_results: list[RetrievalSearchResult] = []
    for score in rerank_result.scores:
        if score.candidate_id in seen_candidate_ids:
            raise RetrievalServiceError("rerank returned duplicate candidate id")
        result = by_candidate_id.get(score.candidate_id)
        if result is None:
            raise RetrievalServiceError("rerank returned unknown candidate id")
        seen_candidate_ids.add(score.candidate_id)
        reranked_results.append(
            _with_rerank_metadata(
                result,
                score=score,
                rerank_result=rerank_result,
                dense_rank=dense_rank_by_candidate_id[score.candidate_id],
                candidate_limit=candidate_limit,
            )
        )

    if not reranked_results:
        raise RetrievalServiceError("rerank returned no scores")
    return reranked_results


def _with_rerank_metadata(
    result: RetrievalSearchResult,
    *,
    score: RerankScore,
    rerank_result: RerankResult,
    dense_rank: int,
    candidate_limit: int,
) -> RetrievalSearchResult:
    return RetrievalSearchResult(
        chunk_id=result.chunk_id,
        distance=result.distance,
        score=result.score,
        citation=result.citation,
        embedding_metadata=(
            dict(result.embedding_metadata)
            if result.embedding_metadata is not None
            else None
        ),
        rerank_metadata={
            "candidate_limit": candidate_limit,
            "dense_rank": dense_rank,
            "rerank_model": rerank_result.model_name,
            "rerank_provider": rerank_result.provider_name,
            "rerank_rank": score.rerank_rank,
            "rerank_score": score.score,
            "score_metadata": dict(score.metadata),
            "used_rerank": True,
        },
    )


def _to_dense_filters(
    metadata_filter: RetrievalMetadataFilter | None,
) -> DenseRetrievalFilters:
    if metadata_filter is None:
        return DenseRetrievalFilters()

    source_type = _normalize_optional_text(
        metadata_filter.source_type,
        field_name="source_type",
    )
    tags = tuple(_normalize_tag(tag) for tag in metadata_filter.tags)
    _validate_range(
        metadata_filter.source_created_at_from,
        metadata_filter.source_created_at_to,
        field_name="source_created_at",
    )
    _validate_range(
        metadata_filter.document_created_at_from,
        metadata_filter.document_created_at_to,
        field_name="document_created_at",
    )
    return DenseRetrievalFilters(
        source_id=metadata_filter.source_id,
        document_id=metadata_filter.document_id,
        source_type=source_type,
        tags=tags,
        source_created_at_from=metadata_filter.source_created_at_from,
        source_created_at_to=metadata_filter.source_created_at_to,
        document_created_at_from=metadata_filter.document_created_at_from,
        document_created_at_to=metadata_filter.document_created_at_to,
    )


def _normalize_optional_text(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise RetrievalServiceError(f"{field_name} must not be empty")
    return normalized


def _normalize_tag(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise RetrievalServiceError("tags must not be empty")
    return normalized


def _validate_range(
    start: datetime | None,
    end: datetime | None,
    *,
    field_name: str,
) -> None:
    if start is not None and end is not None and start > end:
        raise RetrievalServiceError(f"{field_name} range is invalid")

