"""Local sparse retrieval over stored sparse embeddings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import (
    Chunk,
    ChunkSparseEmbedding,
    Document,
    DocumentVersion,
    Source,
)
from adaptive_rag.embeddings import SparseEmbeddingVector, sparse_dot_product
from adaptive_rag.retrieval.dense import (
    DenseRetrievalCitation,
    DenseRetrievalFilters,
)


class SparseRetrievalError(ValueError):
    """Error no retryable de sparse retrieval."""


@dataclass(frozen=True, slots=True)
class SparseRetrievalResult:
    chunk_id: UUID
    distance: float
    score: float
    citation: DenseRetrievalCitation
    embedding_metadata: dict[str, Any] | None
    sparse_metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _CandidateRow:
    chunk: Chunk
    sparse_embedding: ChunkSparseEmbedding
    document_version: DocumentVersion
    document: Document
    source: Source
    score: float


class SparseRetriever:
    """Retrieval sparse local con filtro obligatorio por proyecto."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def search(
        self,
        *,
        project_id: UUID,
        query_vector: SparseEmbeddingVector,
        limit: int = 10,
        filters: DenseRetrievalFilters | None = None,
    ) -> list[SparseRetrievalResult]:
        if limit <= 0:
            raise SparseRetrievalError("limit must be positive")
        active_filters = filters or DenseRetrievalFilters()
        if query_vector.sparse_size == 0:
            return []
        candidates = self._search_in_memory(
            project_id=project_id,
            query_vector=query_vector,
            filters=active_filters,
        )
        candidates.sort(
            key=lambda candidate: (-candidate.score, str(candidate.chunk.id))
        )
        return [
            self._to_result(candidate, sparse_rank=rank)
            for rank, candidate in enumerate(candidates[:limit], start=1)
        ]

    def _search_in_memory(
        self,
        *,
        project_id: UUID,
        query_vector: SparseEmbeddingVector,
        filters: DenseRetrievalFilters,
    ) -> list[_CandidateRow]:
        statement = (
            select(Chunk, ChunkSparseEmbedding, DocumentVersion, Document, Source)
            .join(ChunkSparseEmbedding, ChunkSparseEmbedding.chunk_id == Chunk.id)
            .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .join(Source, Document.source_id == Source.id)
        )
        statement = self._apply_filters(
            statement,
            project_id=project_id,
            filters=filters,
        )

        candidates: list[_CandidateRow] = []
        for row in self._session.execute(statement).all():
            chunk = cast(Chunk, row[0])
            sparse_embedding = cast(ChunkSparseEmbedding, row[1])
            document_version = cast(DocumentVersion, row[2])
            document = cast(Document, row[3])
            source = cast(Source, row[4])
            if not _source_has_tags(source, filters.tags):
                continue
            score = sparse_dot_product(
                query_vector,
                SparseEmbeddingVector(
                    indices=tuple(
                        int(index) for index in sparse_embedding.sparse_indices
                    ),
                    values=tuple(
                        float(value) for value in sparse_embedding.sparse_values
                    ),
                    tokens=(
                        tuple(str(token) for token in sparse_embedding.sparse_tokens)
                        if sparse_embedding.sparse_tokens is not None
                        else None
                    ),
                ),
            )
            if score <= 0:
                continue
            candidates.append(
                _CandidateRow(
                    chunk=chunk,
                    sparse_embedding=sparse_embedding,
                    document_version=document_version,
                    document=document,
                    source=source,
                    score=score,
                )
            )
        return candidates

    def _apply_filters(
        self,
        statement: Any,
        *,
        project_id: UUID,
        filters: DenseRetrievalFilters,
    ) -> Any:
        statement = statement.where(
            Document.project_id == project_id,
            Source.project_id == project_id,
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
        return statement

    def _to_result(
        self,
        candidate: _CandidateRow,
        *,
        sparse_rank: int,
    ) -> SparseRetrievalResult:
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
        return SparseRetrievalResult(
            chunk_id=chunk.id,
            distance=1.0 / (1.0 + candidate.score),
            score=candidate.score,
            citation=citation,
            embedding_metadata=_copy_dict(candidate.sparse_embedding.extra_metadata),
            sparse_metadata={
                "sparse_index_fingerprint": (
                    candidate.sparse_embedding.index_fingerprint
                ),
                "sparse_rank": sparse_rank,
                "sparse_score": candidate.score,
                "used_sparse": True,
            },
        )


def _snippet_for_chunk(*, chunk: Chunk, document_version: DocumentVersion) -> str:
    text = document_version.normalized_text
    if chunk.char_start < 0 or chunk.char_end > len(text):
        raise SparseRetrievalError("chunk offsets are outside document text")
    if chunk.char_end <= chunk.char_start:
        raise SparseRetrievalError("chunk offsets are empty")
    return text[chunk.char_start : chunk.char_end]


def _source_has_tags(source: Source, tags: tuple[str, ...]) -> bool:
    if not tags:
        return True
    source_tags = set(source.tags or [])
    return all(tag in source_tags for tag in tags)


def _copy_dict(value: dict[str, Any] | None) -> dict[str, Any] | None:
    return dict(value) if value is not None else None
