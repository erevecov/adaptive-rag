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
from adaptive_rag.retrieval.dense import (
    DenseRetrievalCitation,
    DenseRetrievalError,
    DenseRetrievalFilters,
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
class RetrievalSearchRequest:
    """Solicitud interna de retrieval sobre query text."""

    project_id: UUID
    query: str
    limit: int = 10
    metadata_filter: RetrievalMetadataFilter | None = None


@dataclass(frozen=True, slots=True)
class RetrievalSearchResult:
    """Resultado de retrieval serializable por futuras superficies API/CLI."""

    chunk_id: UUID
    distance: float
    score: float
    citation: DenseRetrievalCitation
    embedding_metadata: dict[str, Any] | None


class RetrievalService:
    """Genera query embeddings y delega retrieval exacto al baseline M3."""

    def __init__(
        self,
        session: Session,
        *,
        provider: DenseEmbeddingProvider,
    ) -> None:
        self._provider = provider
        self._retriever = DenseRetriever(session)

    def search(self, request: RetrievalSearchRequest) -> list[RetrievalSearchResult]:
        query = _validate_query(request.query)
        if request.limit <= 0:
            raise RetrievalServiceError("limit must be positive")

        filters = _to_dense_filters(request.metadata_filter)
        query_embedding = self._embed_query(query)

        try:
            results = self._retriever.search(
                project_id=request.project_id,
                query_embedding=query_embedding,
                limit=request.limit,
                filters=filters,
            )
        except DenseRetrievalError as exc:
            raise RetrievalServiceError(str(exc)) from exc

        return [
            RetrievalSearchResult(
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
            for result in results
        ]

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


def _validate_query(query: str) -> str:
    value = query.strip()
    if not value:
        raise RetrievalServiceError("query must not be empty")
    return value


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

