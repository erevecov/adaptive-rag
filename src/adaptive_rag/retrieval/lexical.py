"""Local lexical retrieval over chunk lexical input."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

from sqlalchemy import case, desc, func, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Chunk, Document, DocumentVersion, Source
from adaptive_rag.retrieval.dense import (
    DenseRetrievalCitation,
    DenseRetrievalFilters,
)


class LexicalRetrievalError(ValueError):
    """Error no retryable de lexical retrieval."""


@dataclass(frozen=True, slots=True)
class LexicalRetrievalResult:
    chunk_id: UUID
    distance: float
    score: float
    citation: DenseRetrievalCitation
    embedding_metadata: dict[str, Any] | None
    lexical_metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _CandidateRow:
    chunk: Chunk
    document_version: DocumentVersion
    document: Document
    source: Source
    score: float


class LexicalRetriever:
    """Retrieval lexical local con filtro obligatorio por proyecto."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def search(
        self,
        *,
        project_id: UUID,
        query: str,
        limit: int = 10,
        filters: DenseRetrievalFilters | None = None,
    ) -> list[LexicalRetrievalResult]:
        if limit <= 0:
            raise LexicalRetrievalError("limit must be positive")
        active_query = _validate_query(query)
        active_filters = filters or DenseRetrievalFilters()
        if self._dialect_name() == "postgresql":
            candidates = self._search_postgres(
                project_id=project_id,
                query=active_query,
                limit=limit,
                filters=active_filters,
            )
        else:
            candidates = self._search_in_memory(
                project_id=project_id,
                query=active_query,
                limit=limit,
                filters=active_filters,
            )
        return [
            self._to_result(candidate, lexical_rank=rank)
            for rank, candidate in enumerate(candidates, start=1)
        ]

    def _search_postgres(
        self,
        *,
        project_id: UUID,
        query: str,
        limit: int,
        filters: DenseRetrievalFilters,
    ) -> list[_CandidateRow]:
        lexical_input = _postgres_lexical_input_expression()
        query_expr = func.plainto_tsquery("simple", query)
        vector_expr = func.to_tsvector("simple", lexical_input)
        score_expr = func.ts_rank_cd(vector_expr, query_expr).label("lexical_score")
        statement = (
            select(Chunk, DocumentVersion, Document, Source, score_expr)
            .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .join(Source, Document.source_id == Source.id)
            .where(vector_expr.op("@@")(query_expr))
        )
        statement = self._apply_filters(
            statement,
            project_id=project_id,
            filters=filters,
            apply_tags_in_sql=True,
        )
        statement = statement.order_by(desc(score_expr), Chunk.id).limit(limit)
        return [
            _CandidateRow(
                chunk=cast(Chunk, row[0]),
                document_version=cast(DocumentVersion, row[1]),
                document=cast(Document, row[2]),
                source=cast(Source, row[3]),
                score=float(row[4]),
            )
            for row in self._session.execute(statement).all()
        ]

    def _search_in_memory(
        self,
        *,
        project_id: UUID,
        query: str,
        limit: int,
        filters: DenseRetrievalFilters,
    ) -> list[_CandidateRow]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []
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
            if not _source_has_tags(source, filters.tags):
                continue
            snippet = _snippet_for_chunk(
                chunk=chunk,
                document_version=document_version,
            )
            score = _lexical_score(
                query_tokens=query_tokens,
                lexical_input=_lexical_input_text(
                    chunk=chunk,
                    chunk_text=snippet,
                ),
            )
            if score <= 0:
                continue
            candidates.append(
                _CandidateRow(
                    chunk=chunk,
                    document_version=document_version,
                    document=document,
                    source=source,
                    score=score,
                )
            )
        candidates.sort(
            key=lambda candidate: (-candidate.score, str(candidate.chunk.id))
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
            statement = statement.where(
                sql_cast(Source.tags, JSONB).contains(list(filters.tags))
            )
        return statement

    def _to_result(
        self,
        candidate: _CandidateRow,
        *,
        lexical_rank: int,
    ) -> LexicalRetrievalResult:
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
        return LexicalRetrievalResult(
            chunk_id=chunk.id,
            distance=1.0 / (1.0 + candidate.score),
            score=candidate.score,
            citation=citation,
            embedding_metadata=_copy_dict(chunk.embedding_metadata),
            lexical_metadata={
                "lexical_rank": lexical_rank,
                "lexical_score": candidate.score,
                "used_lexical": True,
            },
        )

    def _dialect_name(self) -> str:
        return self._session.get_bind().dialect.name


def _validate_query(query: str) -> str:
    value = query.strip()
    if not value:
        raise LexicalRetrievalError("query must not be empty")
    return value


def _postgres_lexical_input_expression() -> Any:
    chunk_text = func.substr(
        DocumentVersion.normalized_text,
        Chunk.char_start + 1,
        Chunk.char_end - Chunk.char_start,
    )
    summary = func.nullif(Chunk.contextual_summary, "")
    return case(
        (summary.is_not(None), func.concat(summary, "\n\n", chunk_text)),
        else_=chunk_text,
    )


def _lexical_input_text(*, chunk: Chunk, chunk_text: str) -> str:
    contextual_summary = (
        chunk.contextual_summary.strip()
        if isinstance(chunk.contextual_summary, str)
        else ""
    )
    if contextual_summary:
        return f"{contextual_summary}\n\n{chunk_text}"
    return chunk_text


def _lexical_score(
    *,
    query_tokens: Sequence[str],
    lexical_input: str,
) -> float:
    counts = Counter(_tokens(lexical_input))
    return float(sum(counts[token] for token in query_tokens))


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(
        match.group(0).lower() for match in re.finditer(r"[a-zA-Z0-9_]+", value)
    )


def _snippet_for_chunk(*, chunk: Chunk, document_version: DocumentVersion) -> str:
    text = document_version.normalized_text
    if chunk.char_start < 0 or chunk.char_end > len(text):
        raise LexicalRetrievalError("chunk offsets are outside document text")
    if chunk.char_end <= chunk.char_start:
        raise LexicalRetrievalError("chunk offsets are empty")
    return text[chunk.char_start : chunk.char_end]


def _source_has_tags(source: Source, tags: tuple[str, ...]) -> bool:
    if not tags:
        return True
    source_tags = set(source.tags or [])
    return all(tag in source_tags for tag in tags)


def _copy_dict(value: dict[str, Any] | None) -> dict[str, Any] | None:
    return dict(value) if value is not None else None
