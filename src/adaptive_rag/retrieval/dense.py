"""Dense retrieval exacto sobre chunks persistidos."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import (
    EMBEDDING_DIMENSIONS,
    Chunk,
    Document,
    DocumentVersion,
    Source,
)


class DenseRetrievalError(ValueError):
    """Error no retryable del baseline de dense retrieval."""


@dataclass(frozen=True, slots=True)
class DenseRetrievalFilters:
    """Filtros aplicados antes de rankear candidatos."""

    source_id: UUID | None = None
    document_id: UUID | None = None
    source_type: str | None = None
    tags: tuple[str, ...] = ()
    source_created_at_from: datetime | None = None
    source_created_at_to: datetime | None = None
    document_created_at_from: datetime | None = None
    document_created_at_to: datetime | None = None


@dataclass(frozen=True, slots=True)
class DenseRetrievalCitation:
    """Citation anclada al texto normalizado original."""

    source_id: UUID
    source_type: str
    source_external_id: str
    source_tags: tuple[str, ...]
    source_extra_metadata: dict[str, Any] | None
    document_id: UUID
    document_stable_id: str
    document_version_id: UUID
    document_version_number: int
    chunk_id: UUID
    char_start: int
    char_end: int
    snippet: str
    section_metadata: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class DenseRetrievalResult:
    """Resultado rankeado por distancia L2 ascendente."""

    chunk_id: UUID
    distance: float
    score: float
    citation: DenseRetrievalCitation
    embedding_metadata: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class _CandidateRow:
    chunk: Chunk
    document_version: DocumentVersion
    document: Document
    source: Source
    distance: float


class DenseRetriever:
    """Retrieval dense exacto con filtro obligatorio por proyecto."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def search(
        self,
        *,
        project_id: UUID,
        query_embedding: Sequence[float],
        limit: int = 10,
        filters: DenseRetrievalFilters | None = None,
    ) -> list[DenseRetrievalResult]:
        if limit <= 0:
            raise DenseRetrievalError("limit must be positive")

        query_vector = _validate_query_embedding(query_embedding)
        active_filters = filters or DenseRetrievalFilters()
        if self._dialect_name() == "postgresql":
            candidates = self._search_postgres(
                project_id=project_id,
                query_vector=query_vector,
                limit=limit,
                filters=active_filters,
            )
        else:
            candidates = self._search_in_memory(
                project_id=project_id,
                query_vector=query_vector,
                limit=limit,
                filters=active_filters,
            )
        return [self._to_result(candidate) for candidate in candidates]

    def _search_postgres(
        self,
        *,
        project_id: UUID,
        query_vector: list[float],
        limit: int,
        filters: DenseRetrievalFilters,
    ) -> list[_CandidateRow]:
        distance_expr = Chunk.embedding.l2_distance(query_vector).label("distance")
        statement = (
            select(Chunk, DocumentVersion, Document, Source, distance_expr)
            .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .join(Source, Document.source_id == Source.id)
        )
        statement = self._apply_filters(
            statement,
            project_id=project_id,
            filters=filters,
            apply_tags_in_sql=True,
        )
        statement = statement.order_by(distance_expr, Chunk.id).limit(limit)

        rows = self._session.execute(statement).all()
        return [
            _CandidateRow(
                chunk=cast(Chunk, row[0]),
                document_version=cast(DocumentVersion, row[1]),
                document=cast(Document, row[2]),
                source=cast(Source, row[3]),
                distance=float(row[4]),
            )
            for row in rows
        ]

    def _search_in_memory(
        self,
        *,
        project_id: UUID,
        query_vector: list[float],
        limit: int,
        filters: DenseRetrievalFilters,
    ) -> list[_CandidateRow]:
        statement = (
            select(Chunk, DocumentVersion, Document, Source)
            .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .join(Source, Document.source_id == Source.id)
        )
        statement = self._apply_filters(
            statement,
            project_id=project_id,
            filters=filters,
            apply_tags_in_sql=False,
        )

        candidates: list[_CandidateRow] = []
        for row in self._session.execute(statement).all():
            chunk = cast(Chunk, row[0])
            document_version = cast(DocumentVersion, row[1])
            document = cast(Document, row[2])
            source = cast(Source, row[3])
            if chunk.embedding is None:
                continue
            if not _source_has_tags(source, filters.tags):
                continue
            embedding = _validate_stored_embedding(chunk)
            candidates.append(
                _CandidateRow(
                    chunk=chunk,
                    document_version=document_version,
                    document=document,
                    source=source,
                    distance=math.dist(query_vector, embedding),
                )
            )

        candidates.sort(
            key=lambda candidate: (candidate.distance, str(candidate.chunk.id))
        )
        return candidates[:limit]

    def _apply_filters(
        self,
        statement: Any,
        *,
        project_id: UUID,
        filters: DenseRetrievalFilters,
        apply_tags_in_sql: bool,
    ) -> Any:
        statement = statement.where(
            Document.project_id == project_id,
            Source.project_id == project_id,
            Chunk.embedding.is_not(None),
        )

        if filters.source_id is not None:
            statement = statement.where(Source.id == filters.source_id)
        if filters.document_id is not None:
            statement = statement.where(Document.id == filters.document_id)
        if filters.source_type is not None:
            statement = statement.where(Source.source_type == filters.source_type)
        if filters.source_created_at_from is not None:
            statement = statement.where(
                Source.created_at >= filters.source_created_at_from
            )
        if filters.source_created_at_to is not None:
            statement = statement.where(
                Source.created_at <= filters.source_created_at_to
            )
        if filters.document_created_at_from is not None:
            statement = statement.where(
                Document.created_at >= filters.document_created_at_from
            )
        if filters.document_created_at_to is not None:
            statement = statement.where(
                Document.created_at <= filters.document_created_at_to
            )
        if apply_tags_in_sql and filters.tags:
            statement = statement.where(Source.tags.contains(list(filters.tags)))

        return statement

    def _to_result(self, candidate: _CandidateRow) -> DenseRetrievalResult:
        chunk = candidate.chunk
        citation = DenseRetrievalCitation(
            source_id=candidate.source.id,
            source_type=candidate.source.source_type,
            source_external_id=candidate.source.external_id,
            source_tags=tuple(candidate.source.tags or ()),
            source_extra_metadata=_copy_dict(candidate.source.extra_metadata),
            document_id=candidate.document.id,
            document_stable_id=candidate.document.stable_id,
            document_version_id=candidate.document_version.id,
            document_version_number=candidate.document_version.version_number,
            chunk_id=chunk.id,
            char_start=chunk.char_start,
            char_end=chunk.char_end,
            snippet=_snippet_for_chunk(
                chunk=chunk,
                document_version=candidate.document_version,
            ),
            section_metadata=_copy_dict(chunk.section_metadata),
        )
        return DenseRetrievalResult(
            chunk_id=chunk.id,
            distance=candidate.distance,
            score=_score(candidate.distance),
            citation=citation,
            embedding_metadata=_copy_dict(chunk.embedding_metadata),
        )

    def _dialect_name(self) -> str:
        return self._session.get_bind().dialect.name


def _validate_query_embedding(query_embedding: Sequence[float]) -> list[float]:
    values = [float(value) for value in query_embedding]
    if len(values) != EMBEDDING_DIMENSIONS:
        raise DenseRetrievalError(
            "query embedding dimension mismatch: "
            f"expected {EMBEDDING_DIMENSIONS}, got {len(values)}"
        )
    return values


def _validate_stored_embedding(chunk: Chunk) -> list[float]:
    if chunk.embedding is None:
        raise DenseRetrievalError("chunk embedding is missing")

    values = [float(value) for value in chunk.embedding]
    if len(values) != EMBEDDING_DIMENSIONS:
        raise DenseRetrievalError(
            "stored embedding dimension mismatch: "
            f"expected {EMBEDDING_DIMENSIONS}, got {len(values)}"
        )
    return values


def _snippet_for_chunk(*, chunk: Chunk, document_version: DocumentVersion) -> str:
    text = document_version.normalized_text
    if chunk.char_start < 0 or chunk.char_end > len(text):
        raise DenseRetrievalError("chunk offsets are outside document text")
    if chunk.char_end <= chunk.char_start:
        raise DenseRetrievalError("chunk offsets are empty")
    return text[chunk.char_start : chunk.char_end]


def _source_has_tags(source: Source, tags: tuple[str, ...]) -> bool:
    if not tags:
        return True
    source_tags = set(source.tags or [])
    return all(tag in source_tags for tag in tags)


def _score(distance: float) -> float:
    return 1.0 / (1.0 + distance)


def _copy_dict(value: dict[str, Any] | None) -> dict[str, Any] | None:
    return dict(value) if value is not None else None
