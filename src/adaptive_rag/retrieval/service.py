"""Servicio compartido para la superficie de retrieval M4."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, cast
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.db.models import CHAT_RETRIEVAL_MAX_LIMIT, EMBEDDING_DIMENSIONS
from adaptive_rag.db.repositories import GraphprojectionRepository
from adaptive_rag.embeddings import (
    DenseEmbeddingProvider,
    QwenEmbeddingProviderError,
    SparseEmbeddingProvider,
)
from adaptive_rag.graph import (
    GraphRetrievalResult,
    GraphRetriever,
    GraphStoreError,
    should_use_dense_fallback,
)
from adaptive_rag.provider_usage import ProviderBudgetExceededError
from adaptive_rag.rerank import (
    RerankCandidate,
    RerankProvider,
    RerankProviderError,
    RerankRequest,
    RerankResult,
    RerankScore,
)
from adaptive_rag.retrieval.bm25 import (
    Bm25RetrievalError,
    Bm25RetrievalResult,
    Bm25Retriever,
)
from adaptive_rag.retrieval.dense import (
    DenseRetrievalCitation,
    DenseRetrievalError,
    DenseRetrievalFilters,
    DenseRetrievalResult,
    DenseRetriever,
)
from adaptive_rag.retrieval.lexical import (
    LexicalRetrievalError,
    LexicalRetrievalResult,
    LexicalRetriever,
)
from adaptive_rag.retrieval.sparse import (
    SparseRetrievalError,
    SparseRetrievalResult,
    SparseRetriever,
)


class RetrievalServiceError(ValueError):
    """Error no retryable de la superficie compartida de retrieval."""


class _RerankResultValidationError(ValueError):
    """Error conocido al aplicar una respuesta invalida de rerank."""


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


RetrievalStrategy = Literal[
    "dense",
    "graph",
    "lexical",
    "bm25",
    "sparse",
    "hybrid_rrf",
    "dense_sparse",
]
RerankFallbackReason = Literal[
    "rerank_not_configured",
    "rerank_unavailable",
    "rerank_budget_exceeded",
]
RRF_K = 60
SPARSE_FALLBACK_UNAVAILABLE = "sparse_provider_unavailable"
SPARSE_FALLBACK_PROVIDER_ERROR = "sparse_provider_error"
SPARSE_FALLBACK_QUERY_EMBED = "sparse_query_embed_failed"
SPARSE_FALLBACK_RETRIEVAL = "sparse_retrieval_failed"


@dataclass(frozen=True, slots=True)
class RetrievalSearchRequest:
    """Solicitud interna de retrieval sobre query text."""

    workspace_id: UUID
    query: str
    limit: int = 10
    metadata_filter: RetrievalMetadataFilter | None = None
    rerank: RetrievalRerankOptions | None = None
    strategy: RetrievalStrategy = "dense_sparse"


@dataclass(frozen=True, slots=True)
class RetrievalSearchResult:
    """Resultado de retrieval serializable por futuras superficies API/CLI."""

    chunk_id: UUID
    distance: float
    score: float
    citation: DenseRetrievalCitation
    embedding_metadata: dict[str, Any] | None
    retrieval_metadata: dict[str, Any] | None = None
    rerank_metadata: dict[str, Any] | None = None
    strategy: RetrievalStrategy = "dense"
    fallback_reason: str | None = None


@dataclass(frozen=True, slots=True)
class _GraphRetrievalAttempt:
    results: list[RetrievalSearchResult] | None
    fallback_reason: str | None = None


class RetrievalService:
    """Genera query embeddings y delega retrieval exacto al baseline M3."""

    def __init__(
        self,
        session: Session,
        *,
        provider: DenseEmbeddingProvider,
        sparse_provider: SparseEmbeddingProvider | None = None,
        reranker: RerankProvider | None = None,
        graph_retriever: GraphRetriever | None = None,
        graph_projection_repository: GraphprojectionRepository | None = None,
    ) -> None:
        self._provider = provider
        self._sparse_provider = sparse_provider
        self._reranker = reranker
        self._retriever = DenseRetriever(session)
        self._lexical_retriever = LexicalRetriever(session)
        self._bm25_retriever = Bm25Retriever(session)
        self._sparse_retriever = SparseRetriever(session)
        self._graph_retriever = graph_retriever
        self._graph_projection_repository = (
            graph_projection_repository or GraphprojectionRepository(session)
        )

    def search(self, request: RetrievalSearchRequest) -> list[RetrievalSearchResult]:
        query = _validate_query(request.query)
        limit = _validate_limit(request.limit)
        strategy = _validate_strategy(request.strategy)
        rerank_options = _validate_rerank_options(
            request.rerank,
            limit=limit,
        )

        filters = _to_dense_filters(request.metadata_filter)
        candidate_limit = (
            rerank_options.candidate_limit if rerank_options is not None else limit
        )

        if strategy == "lexical":
            search_results = self._lexical_results(
                workspace_id=request.workspace_id,
                query=query,
                limit=candidate_limit,
                filters=filters,
            )
        elif strategy == "bm25":
            search_results = self._bm25_results(
                workspace_id=request.workspace_id,
                query=query,
                limit=candidate_limit,
                filters=filters,
            )
        elif strategy == "sparse":
            sparse_hits, reason = self._try_sparse_results(
                workspace_id=request.workspace_id,
                query=query,
                limit=candidate_limit,
                filters=filters,
            )
            if sparse_hits is not None:
                search_results = [
                    _to_sparse_search_result(result) for result in sparse_hits
                ]
            else:
                search_results = [
                    _with_fallback_reason(
                        result,
                        reason or SPARSE_FALLBACK_UNAVAILABLE,
                    )
                    for result in self._bm25_results(
                        workspace_id=request.workspace_id,
                        query=query,
                        limit=candidate_limit,
                        filters=filters,
                    )
                ]
        else:
            query_embedding = self._embed_query(query)
            try:
                dense_results = self._retriever.search(
                    workspace_id=request.workspace_id,
                    query_embedding=query_embedding,
                    limit=candidate_limit,
                    filters=filters,
                )
            except DenseRetrievalError as exc:
                raise RetrievalServiceError(str(exc)) from exc

            if strategy == "hybrid_rrf":
                lexical_results = self._raw_lexical_results(
                    workspace_id=request.workspace_id,
                    query=query,
                    limit=candidate_limit,
                    filters=filters,
                )
                search_results = _fuse_rrf_results(
                    dense_results=dense_results,
                    lexical_results=lexical_results,
                    limit=candidate_limit,
                    strategy="hybrid_rrf",
                )
            elif strategy == "dense_sparse":
                sparse_hits, reason = self._try_sparse_results(
                    workspace_id=request.workspace_id,
                    query=query,
                    limit=candidate_limit,
                    filters=filters,
                )
                if sparse_hits is not None:
                    search_results = _fuse_rrf_results(
                        dense_results=dense_results,
                        sparse_results=sparse_hits,
                        limit=candidate_limit,
                        strategy="dense_sparse",
                    )
                else:
                    bm25_hits = self._raw_bm25_results(
                        workspace_id=request.workspace_id,
                        query=query,
                        limit=candidate_limit,
                        filters=filters,
                    )
                    search_results = _fuse_rrf_results(
                        dense_results=dense_results,
                        bm25_results=bm25_hits,
                        limit=candidate_limit,
                        strategy="dense_sparse",
                    )
                    search_results = [
                        _with_fallback_reason(
                            result,
                            reason or SPARSE_FALLBACK_UNAVAILABLE,
                        )
                        for result in search_results
                    ]
            else:
                search_results = [_to_search_result(result) for result in dense_results]
                if strategy == "graph":
                    graph_attempt = self._try_graph_results(
                        workspace_id=request.workspace_id,
                        dense_results=dense_results,
                        limit=candidate_limit,
                        filters=filters,
                    )
                    if graph_attempt.results is not None:
                        search_results = graph_attempt.results
                    elif graph_attempt.fallback_reason is not None:
                        search_results = [
                            _with_fallback_reason(
                                result,
                                graph_attempt.fallback_reason,
                            )
                            for result in search_results
                        ]
        if rerank_options is None or not search_results:
            return search_results
        return self._rerank_results(
            query=query,
            results=search_results,
            limit=limit,
            options=rerank_options,
        )

    def _lexical_results(
        self,
        *,
        workspace_id: UUID,
        query: str,
        limit: int,
        filters: DenseRetrievalFilters,
    ) -> list[RetrievalSearchResult]:
        return [
            _to_lexical_search_result(result)
            for result in self._raw_lexical_results(
                workspace_id=workspace_id,
                query=query,
                limit=limit,
                filters=filters,
            )
        ]

    def _raw_lexical_results(
        self,
        *,
        workspace_id: UUID,
        query: str,
        limit: int,
        filters: DenseRetrievalFilters,
    ) -> list[LexicalRetrievalResult]:
        try:
            return self._lexical_retriever.search(
                workspace_id=workspace_id,
                query=query,
                limit=limit,
                filters=filters,
            )
        except LexicalRetrievalError as exc:
            raise RetrievalServiceError(str(exc)) from exc

    def _bm25_results(
        self,
        *,
        workspace_id: UUID,
        query: str,
        limit: int,
        filters: DenseRetrievalFilters,
    ) -> list[RetrievalSearchResult]:
        return [
            _to_bm25_search_result(result)
            for result in self._raw_bm25_results(
                workspace_id=workspace_id,
                query=query,
                limit=limit,
                filters=filters,
            )
        ]

    def _raw_bm25_results(
        self,
        *,
        workspace_id: UUID,
        query: str,
        limit: int,
        filters: DenseRetrievalFilters,
    ) -> list[Bm25RetrievalResult]:
        try:
            return self._bm25_retriever.search(
                workspace_id=workspace_id,
                query=query,
                limit=limit,
                filters=filters,
            )
        except Bm25RetrievalError as exc:
            raise RetrievalServiceError(str(exc)) from exc

    def _raw_sparse_results(
        self,
        *,
        workspace_id: UUID,
        query: str,
        limit: int,
        filters: DenseRetrievalFilters,
    ) -> list[SparseRetrievalResult]:
        if self._sparse_provider is None:
            raise RetrievalServiceError(
                "sparse embedding provider is required for dense_sparse retrieval"
            )
        try:
            query_vector = self._sparse_provider.embed_query(query)
            return self._sparse_retriever.search(
                workspace_id=workspace_id,
                query_vector=query_vector,
                limit=limit,
                filters=filters,
            )
        except SparseRetrievalError as exc:
            raise RetrievalServiceError(str(exc)) from exc

    def _try_sparse_results(
        self,
        *,
        workspace_id: UUID,
        query: str,
        limit: int,
        filters: DenseRetrievalFilters,
    ) -> tuple[list[SparseRetrievalResult] | None, str | None]:
        """Return (sparse_hits, None) or (None, fallback_reason)."""
        if self._sparse_provider is None:
            return None, SPARSE_FALLBACK_UNAVAILABLE
        try:
            query_vector = self._sparse_provider.embed_query(query)
        except ProviderBudgetExceededError:
            raise
        except QwenEmbeddingProviderError:
            return None, SPARSE_FALLBACK_PROVIDER_ERROR
        try:
            hits = self._sparse_retriever.search(
                workspace_id=workspace_id,
                query_vector=query_vector,
                limit=limit,
                filters=filters,
            )
        except SparseRetrievalError:
            return None, SPARSE_FALLBACK_RETRIEVAL
        return hits, None

    def _sparse_results(
        self,
        *,
        workspace_id: UUID,
        query: str,
        limit: int,
        filters: DenseRetrievalFilters,
    ) -> list[RetrievalSearchResult]:
        return [
            _to_sparse_search_result(result)
            for result in self._raw_sparse_results(
                workspace_id=workspace_id,
                query=query,
                limit=limit,
                filters=filters,
            )
        ]

    def _try_graph_results(
        self,
        *,
        workspace_id: UUID,
        dense_results: list[DenseRetrievalResult],
        limit: int,
        filters: DenseRetrievalFilters,
    ) -> _GraphRetrievalAttempt:
        if self._graph_retriever is None:
            return _GraphRetrievalAttempt(
                results=None,
                fallback_reason="graph_retriever_unavailable",
            )
        projection = self._graph_projection_repository.get(workspace_id=workspace_id)
        if projection is None:
            return _GraphRetrievalAttempt(
                results=None,
                fallback_reason="graph_projection_missing",
            )
        if should_use_dense_fallback(projection.status):
            return _GraphRetrievalAttempt(
                results=None,
                fallback_reason=f"graph_projection_{projection.status}",
            )

        seed_chunk_ids = tuple(result.chunk_id for result in dense_results)
        if not seed_chunk_ids:
            return _GraphRetrievalAttempt(results=[])
        try:
            graph_hits = self._graph_retriever.expand_workspace_chunks(
                workspace_id=workspace_id,
                seed_chunk_ids=seed_chunk_ids,
                limit=limit,
            )
        except GraphStoreError as exc:
            return _GraphRetrievalAttempt(
                results=None,
                fallback_reason=exc.error_code,
            )
        if not graph_hits:
            return _GraphRetrievalAttempt(results=[])
        return _GraphRetrievalAttempt(
            results=self._to_graph_search_results(
                workspace_id=workspace_id,
                graph_hits=graph_hits,
                filters=filters,
            )
        )

    def _to_graph_search_results(
        self,
        *,
        workspace_id: UUID,
        graph_hits: Sequence[GraphRetrievalResult],
        filters: DenseRetrievalFilters,
    ) -> list[RetrievalSearchResult]:
        citations_by_chunk_id = self._retriever.get_by_chunk_ids(
            workspace_id=workspace_id,
            chunk_ids=[hit.chunk_id for hit in graph_hits],
            filters=filters,
        )
        results: list[RetrievalSearchResult] = []
        seen_chunk_ids: set[UUID] = set()
        for hit in graph_hits:
            if hit.chunk_id in seen_chunk_ids:
                continue
            source = citations_by_chunk_id.get(hit.chunk_id)
            if source is None:
                continue
            seen_chunk_ids.add(hit.chunk_id)
            results.append(
                RetrievalSearchResult(
                    chunk_id=hit.chunk_id,
                    distance=hit.distance,
                    score=hit.score,
                    citation=source.citation,
                    embedding_metadata=source.embedding_metadata,
                    strategy="graph",
                )
            )
        return results

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
            return _fallback_rerank_results(
                results,
                limit=limit,
                candidate_limit=options.candidate_limit,
                reason="rerank_not_configured",
            )

        top_k = min(limit, len(results))
        candidates = tuple(
            RerankCandidate(
                candidate_id=str(result.chunk_id),
                text=result.citation.snippet,
                metadata={
                    "chunk_id": str(result.chunk_id),
                    "dense_rank": dense_rank,
                    "retrieval_metadata": _copy_metadata(result.retrieval_metadata),
                },
            )
            for dense_rank, result in enumerate(results, start=1)
        )
        try:
            request = RerankRequest(query=query, candidates=candidates, top_k=top_k)
            rerank_result = self._reranker.rerank(request)
        except ProviderBudgetExceededError:
            return _fallback_rerank_results(
                results,
                limit=limit,
                candidate_limit=options.candidate_limit,
                reason="rerank_budget_exceeded",
            )
        except RerankProviderError:
            return _fallback_rerank_results(
                results,
                limit=limit,
                candidate_limit=options.candidate_limit,
                reason="rerank_unavailable",
            )

        try:
            return _apply_rerank_result(
                results=results,
                rerank_result=rerank_result,
                candidate_limit=options.candidate_limit,
            )
        except _RerankResultValidationError:
            return _fallback_rerank_results(
                results,
                limit=limit,
                candidate_limit=options.candidate_limit,
                reason="rerank_unavailable",
            )


def _validate_query(query: str) -> str:
    value = query.strip()
    if not value:
        raise RetrievalServiceError("query must not be empty")
    return value


def _validate_strategy(strategy: str) -> RetrievalStrategy:
    if strategy not in (
        "dense",
        "graph",
        "lexical",
        "bm25",
        "sparse",
        "hybrid_rrf",
        "dense_sparse",
    ):
        raise RetrievalServiceError(
            "retrieval strategy must be dense, graph, lexical, bm25, "
            "sparse, hybrid_rrf or dense_sparse"
        )
    return cast(RetrievalStrategy, strategy)


def _validate_limit(limit: int) -> int:
    if limit <= 0:
        raise RetrievalServiceError("limit must be positive")
    if limit > CHAT_RETRIEVAL_MAX_LIMIT:
        raise RetrievalServiceError(
            f"limit must be between 1 and {CHAT_RETRIEVAL_MAX_LIMIT}"
        )
    return limit


def _validate_rerank_options(
    rerank_options: RetrievalRerankOptions | None,
    *,
    limit: int,
) -> RetrievalRerankOptions | None:
    if rerank_options is None:
        return None
    if rerank_options.candidate_limit <= 0:
        raise RetrievalServiceError("rerank candidate_limit must be positive")
    if rerank_options.candidate_limit > CHAT_RETRIEVAL_MAX_LIMIT:
        raise RetrievalServiceError(
            f"rerank candidate_limit must be between 1 and {CHAT_RETRIEVAL_MAX_LIMIT}"
        )
    if rerank_options.candidate_limit < limit:
        raise RetrievalServiceError(
            "rerank candidate_limit must be greater than or equal to limit"
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


def _to_lexical_search_result(
    result: LexicalRetrievalResult,
) -> RetrievalSearchResult:
    return RetrievalSearchResult(
        chunk_id=result.chunk_id,
        distance=result.distance,
        score=result.score,
        citation=result.citation,
        embedding_metadata=_copy_metadata(result.embedding_metadata),
        retrieval_metadata=dict(result.lexical_metadata),
        strategy="lexical",
    )


def _to_bm25_search_result(
    result: Bm25RetrievalResult,
) -> RetrievalSearchResult:
    return RetrievalSearchResult(
        chunk_id=result.chunk_id,
        distance=result.distance,
        score=result.score,
        citation=result.citation,
        embedding_metadata=_copy_metadata(result.embedding_metadata),
        retrieval_metadata=dict(result.bm25_metadata),
        strategy="bm25",
    )


def _to_sparse_search_result(
    result: SparseRetrievalResult,
) -> RetrievalSearchResult:
    return RetrievalSearchResult(
        chunk_id=result.chunk_id,
        distance=result.distance,
        score=result.score,
        citation=result.citation,
        embedding_metadata=_copy_metadata(result.embedding_metadata),
        retrieval_metadata=dict(result.sparse_metadata),
        strategy="sparse",
    )


def _with_fallback_reason(
    result: RetrievalSearchResult,
    fallback_reason: str,
) -> RetrievalSearchResult:
    return RetrievalSearchResult(
        chunk_id=result.chunk_id,
        distance=result.distance,
        score=result.score,
        citation=result.citation,
        embedding_metadata=_copy_metadata(result.embedding_metadata),
        retrieval_metadata=_copy_metadata(result.retrieval_metadata),
        rerank_metadata=_copy_metadata(result.rerank_metadata),
        strategy=result.strategy,
        fallback_reason=fallback_reason,
    )


def _fallback_rerank_results(
    results: list[RetrievalSearchResult],
    *,
    limit: int,
    candidate_limit: int,
    reason: RerankFallbackReason,
) -> list[RetrievalSearchResult]:
    return [
        RetrievalSearchResult(
            chunk_id=result.chunk_id,
            distance=result.distance,
            score=result.score,
            citation=result.citation,
            embedding_metadata=_copy_metadata(result.embedding_metadata),
            retrieval_metadata=_copy_metadata(result.retrieval_metadata),
            rerank_metadata={
                "candidate_limit": candidate_limit,
                "fallback_reason": reason,
                "used_rerank": False,
            },
            strategy=result.strategy,
            fallback_reason=result.fallback_reason or reason,
        )
        for result in results[:limit]
    ]


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
            raise _RerankResultValidationError("rerank returned duplicate candidate id")
        result = by_candidate_id.get(score.candidate_id)
        if result is None:
            raise _RerankResultValidationError("rerank returned unknown candidate id")
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
        raise _RerankResultValidationError("rerank returned no scores")
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
        embedding_metadata=_copy_metadata(result.embedding_metadata),
        retrieval_metadata=_copy_metadata(result.retrieval_metadata),
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
        strategy=result.strategy,
        fallback_reason=result.fallback_reason,
    )


def _fuse_rrf_results(
    *,
    dense_results: list[DenseRetrievalResult],
    lexical_results: Sequence[LexicalRetrievalResult] = (),
    sparse_results: Sequence[SparseRetrievalResult] = (),
    bm25_results: Sequence[Bm25RetrievalResult] = (),
    limit: int,
    strategy: Literal["hybrid_rrf", "dense_sparse"],
) -> list[RetrievalSearchResult]:
    by_chunk_id: dict[UUID, _RRFAccumulator] = {}
    for rank, dense_result in enumerate(dense_results, start=1):
        accumulator = by_chunk_id.setdefault(
            dense_result.chunk_id,
            _RRFAccumulator(chunk_id=dense_result.chunk_id),
        )
        accumulator.dense_result = dense_result
        accumulator.dense_rank = rank
        accumulator.rrf_score += _rrf_score(rank)
    for rank, lexical_result in enumerate(lexical_results, start=1):
        accumulator = by_chunk_id.setdefault(
            lexical_result.chunk_id,
            _RRFAccumulator(chunk_id=lexical_result.chunk_id),
        )
        accumulator.lexical_result = lexical_result
        accumulator.lexical_rank = rank
        accumulator.rrf_score += _rrf_score(rank)
    for rank, sparse_result in enumerate(sparse_results, start=1):
        accumulator = by_chunk_id.setdefault(
            sparse_result.chunk_id,
            _RRFAccumulator(chunk_id=sparse_result.chunk_id),
        )
        accumulator.sparse_result = sparse_result
        accumulator.sparse_rank = rank
        accumulator.rrf_score += _rrf_score(rank)
    for rank, bm25_result in enumerate(bm25_results, start=1):
        accumulator = by_chunk_id.setdefault(
            bm25_result.chunk_id,
            _RRFAccumulator(chunk_id=bm25_result.chunk_id),
        )
        accumulator.bm25_result = bm25_result
        accumulator.bm25_rank = rank
        accumulator.rrf_score += _rrf_score(rank)

    accumulators = sorted(
        by_chunk_id.values(),
        key=lambda accumulator: (
            -accumulator.rrf_score,
            accumulator.dense_rank if accumulator.dense_rank is not None else 10**9,
            (
                accumulator.lexical_rank
                if accumulator.lexical_rank is not None
                else 10**9
            ),
            (accumulator.sparse_rank if accumulator.sparse_rank is not None else 10**9),
            (accumulator.bm25_rank if accumulator.bm25_rank is not None else 10**9),
            str(accumulator.chunk_id),
        ),
    )
    return [
        _to_rrf_search_result(accumulator, strategy=strategy)
        for accumulator in accumulators[:limit]
    ]


@dataclass(slots=True)
class _RRFAccumulator:
    chunk_id: UUID
    rrf_score: float = 0.0
    dense_rank: int | None = None
    lexical_rank: int | None = None
    sparse_rank: int | None = None
    bm25_rank: int | None = None
    dense_result: DenseRetrievalResult | None = None
    lexical_result: LexicalRetrievalResult | None = None
    sparse_result: SparseRetrievalResult | None = None
    bm25_result: Bm25RetrievalResult | None = None


def _to_rrf_search_result(
    accumulator: _RRFAccumulator,
    *,
    strategy: Literal["hybrid_rrf", "dense_sparse"],
) -> RetrievalSearchResult:
    source = (
        accumulator.dense_result
        or accumulator.lexical_result
        or accumulator.sparse_result
        or accumulator.bm25_result
    )
    if source is None:
        raise RetrievalServiceError("RRF accumulator has no retrieval result")

    metadata: dict[str, Any] = {
        "rrf_k": RRF_K,
        "rrf_score": accumulator.rrf_score,
        "source_strategies": _rrf_source_strategies(accumulator),
        "used_rrf": True,
    }
    if accumulator.dense_result is not None and accumulator.dense_rank is not None:
        metadata["dense_rank"] = accumulator.dense_rank
        metadata["dense_score"] = accumulator.dense_result.score
    if accumulator.lexical_result is not None and accumulator.lexical_rank is not None:
        metadata["lexical_rank"] = accumulator.lexical_rank
        metadata["lexical_score"] = accumulator.lexical_result.score
    if accumulator.sparse_result is not None and accumulator.sparse_rank is not None:
        metadata["sparse_rank"] = accumulator.sparse_rank
        metadata["sparse_score"] = accumulator.sparse_result.score
        sparse_metadata = accumulator.sparse_result.sparse_metadata
        metadata["sparse_index_fingerprint"] = sparse_metadata[
            "sparse_index_fingerprint"
        ]
    if accumulator.bm25_result is not None and accumulator.bm25_rank is not None:
        metadata["bm25_rank"] = accumulator.bm25_rank
        metadata["bm25_score"] = accumulator.bm25_result.score
        metadata["used_bm25"] = True

    return RetrievalSearchResult(
        chunk_id=source.chunk_id,
        distance=1.0 / (1.0 + accumulator.rrf_score),
        score=accumulator.rrf_score,
        citation=source.citation,
        embedding_metadata=_copy_metadata(source.embedding_metadata),
        retrieval_metadata=metadata,
        strategy=strategy,
    )


def _rrf_source_strategies(accumulator: _RRFAccumulator) -> list[str]:
    strategies: list[str] = []
    if accumulator.dense_result is not None:
        strategies.append("dense")
    if accumulator.lexical_result is not None:
        strategies.append("lexical")
    if accumulator.sparse_result is not None:
        strategies.append("sparse")
    if accumulator.bm25_result is not None:
        strategies.append("bm25")
    return strategies


def _rrf_score(rank: int) -> float:
    return 1.0 / (RRF_K + rank)


def _copy_metadata(value: dict[str, Any] | None) -> dict[str, Any] | None:
    return dict(value) if value is not None else None


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
