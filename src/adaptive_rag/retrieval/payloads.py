"""Payloads serializables compartidos para superficies de retrieval."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from adaptive_rag.retrieval.service import RetrievalSearchResult


class RetrievalCitationPayload(TypedDict):
    source_id: str
    source_type: str
    source_external_id: str
    source_tags: list[str]
    source_extra_metadata: dict[str, Any] | None
    document_id: str
    document_stable_id: str
    document_version_id: str
    document_version_number: int
    chunk_id: str
    char_start: int
    char_end: int
    snippet: str
    section_metadata: dict[str, Any] | None


class RetrievalResultPayload(TypedDict):
    chunk_id: str
    distance: float
    score: float
    citation: RetrievalCitationPayload
    embedding_metadata: dict[str, Any] | None
    strategy: str
    fallback_reason: NotRequired[str]
    rerank_metadata: NotRequired[dict[str, Any]]


def serialize_retrieval_results(
    results: list[RetrievalSearchResult],
) -> list[RetrievalResultPayload]:
    return [serialize_retrieval_result(result) for result in results]


def serialize_retrieval_result(result: RetrievalSearchResult) -> RetrievalResultPayload:
    citation = result.citation
    payload: RetrievalResultPayload = {
        "chunk_id": str(result.chunk_id),
        "distance": result.distance,
        "score": result.score,
        "citation": {
            "source_id": str(citation.source_id),
            "source_type": citation.source_type,
            "source_external_id": citation.source_external_id,
            "source_tags": list(citation.source_tags),
            "source_extra_metadata": _copy_dict(citation.source_extra_metadata),
            "document_id": str(citation.document_id),
            "document_stable_id": citation.document_stable_id,
            "document_version_id": str(citation.document_version_id),
            "document_version_number": citation.document_version_number,
            "chunk_id": str(citation.chunk_id),
            "char_start": citation.char_start,
            "char_end": citation.char_end,
            "snippet": citation.snippet,
            "section_metadata": _copy_dict(citation.section_metadata),
        },
        "embedding_metadata": _copy_dict(result.embedding_metadata),
        "strategy": result.strategy,
    }
    if result.fallback_reason is not None:
        payload["fallback_reason"] = result.fallback_reason
    if result.rerank_metadata is not None:
        payload["rerank_metadata"] = _copy_dict(result.rerank_metadata) or {}
    return payload


def _copy_dict(value: dict[str, Any] | None) -> dict[str, Any] | None:
    return dict(value) if value is not None else None

