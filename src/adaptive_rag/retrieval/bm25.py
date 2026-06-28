"""Local Okapi BM25 retrieval over chunk lexical input."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Chunk, Document, DocumentVersion, Source
from adaptive_rag.retrieval.dense import (
    DenseRetrievalCitation,
    DenseRetrievalFilters,
)

BM25_K1 = 1.2
BM25_B = 0.75


class Bm25RetrievalError(ValueError):
    """Error no retryable de BM25 retrieval."""


@dataclass(frozen=True, slots=True)
class Bm25RetrievalResult:
    chunk_id: UUID
    distance: float
    score: float
    citation: DenseRetrievalCitation
    embedding_metadata: dict[str, Any] | None
    bm25_metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _CandidateRow:
    chunk: Chunk
    document_version: DocumentVersion
    document: Document
    source: Source
    tokens: tuple[str, ...]
    score: float = 0.0


class Bm25Retriever:
    """Okapi BM25 local con filtro obligatorio por proyecto."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def search(
        self,
        *,
        project_id: UUID,
        query: str,
        limit: int = 10,
        filters: DenseRetrievalFilters | None = None,
    ) -> list[Bm25RetrievalResult]:
        if limit <= 0:
            raise Bm25RetrievalError("limit must be positive")
        query_tokens = _tokens(_validate_query(query))
        if not query_tokens:
            return []
        active_filters = filters or DenseRetrievalFilters()
        candidates = self._candidate_rows(
            project_id=project_id,
            filters=active_filters,
        )
        scored = _score_candidates(
            candidates,
            query_terms=_unique_terms(query_tokens),
        )
        return [
            self._to_result(candidate, bm25_rank=rank)
            for rank, candidate in enumerate(scored[:limit], start=1)
        ]

    def _candidate_rows(
        self,
        *,
        project_id: UUID,
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
        )

        candidates: list[_CandidateRow] = []
        for row in self._session.execute(statement).all():
            chunk = cast(Chunk, row[0])
            document_version = cast(DocumentVersion, row[1])
            document = cast(Document, row[2])
            source = cast(Source, row[3])
            if not _source_has_tags(source, filters.tags):
                continue
            snippet = _snippet_for_chunk(
                chunk=chunk,
                document_version=document_version,
            )
            tokens = _tokens(
                _lexical_input_text(
                    chunk=chunk,
                    chunk_text=snippet,
                )
            )
            if not tokens:
                continue
            candidates.append(
                _CandidateRow(
                    chunk=chunk,
                    document_version=document_version,
                    document=document,
                    source=source,
                    tokens=tokens,
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
        bm25_rank: int,
    ) -> Bm25RetrievalResult:
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
        return Bm25RetrievalResult(
            chunk_id=chunk.id,
            distance=1.0 / (1.0 + candidate.score),
            score=candidate.score,
            citation=citation,
            embedding_metadata=_copy_dict(chunk.embedding_metadata),
            bm25_metadata={
                "bm25_rank": bm25_rank,
                "bm25_score": candidate.score,
                "used_bm25": True,
            },
        )


def _score_candidates(
    candidates: Sequence[_CandidateRow],
    *,
    query_terms: tuple[str, ...],
) -> list[_CandidateRow]:
    if not candidates:
        return []
    avg_doc_len = sum(len(candidate.tokens) for candidate in candidates) / len(
        candidates
    )
    if avg_doc_len <= 0:
        return []
    document_frequency = Counter(
        term
        for candidate in candidates
        for term in set(candidate.tokens)
        if term in query_terms
    )
    scored: list[_CandidateRow] = []
    for candidate in candidates:
        score = _bm25_score(
            tokens=candidate.tokens,
            query_terms=query_terms,
            document_frequency=document_frequency,
            document_count=len(candidates),
            avg_doc_len=avg_doc_len,
        )
        if score <= 0:
            continue
        scored.append(
            _CandidateRow(
                chunk=candidate.chunk,
                document_version=candidate.document_version,
                document=candidate.document,
                source=candidate.source,
                tokens=candidate.tokens,
                score=score,
            )
        )
    scored.sort(key=lambda candidate: (-candidate.score, str(candidate.chunk.id)))
    return scored


def _bm25_score(
    *,
    tokens: tuple[str, ...],
    query_terms: tuple[str, ...],
    document_frequency: Counter[str],
    document_count: int,
    avg_doc_len: float,
) -> float:
    counts = Counter(tokens)
    doc_len = len(tokens)
    score = 0.0
    for term in query_terms:
        term_frequency = counts[term]
        if term_frequency <= 0:
            continue
        df = document_frequency[term]
        if df <= 0:
            continue
        idf = math.log(1.0 + (document_count - df + 0.5) / (df + 0.5))
        denominator = term_frequency + BM25_K1 * (
            1.0 - BM25_B + BM25_B * doc_len / avg_doc_len
        )
        score += idf * (term_frequency * (BM25_K1 + 1.0)) / denominator
    return score


def _validate_query(query: str) -> str:
    value = query.strip()
    if not value:
        raise Bm25RetrievalError("query must not be empty")
    return value


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(
        match.group(0).casefold() for match in re.finditer(r"\w+", value)
    )


def _unique_terms(tokens: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(tokens))


def _lexical_input_text(*, chunk: Chunk, chunk_text: str) -> str:
    contextual_summary = (
        chunk.contextual_summary.strip()
        if isinstance(chunk.contextual_summary, str)
        else ""
    )
    if contextual_summary:
        return f"{contextual_summary}\n\n{chunk_text}"
    return chunk_text


def _snippet_for_chunk(*, chunk: Chunk, document_version: DocumentVersion) -> str:
    text = document_version.normalized_text
    if chunk.char_start < 0 or chunk.char_end > len(text):
        raise Bm25RetrievalError("chunk offsets are outside document text")
    if chunk.char_end <= chunk.char_start:
        raise Bm25RetrievalError("chunk offsets are empty")
    return text[chunk.char_start : chunk.char_end]


def _source_has_tags(source: Source, tags: tuple[str, ...]) -> bool:
    if not tags:
        return True
    source_tags = set(source.tags or [])
    return all(tag in source_tags for tag in tags)


def _copy_dict(value: dict[str, Any] | None) -> dict[str, Any] | None:
    return dict(value) if value is not None else None
