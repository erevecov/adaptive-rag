"""Schemas HTTP para la superficie de retrieval."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    SerializerFunctionWrapHandler,
    model_serializer,
)

from adaptive_rag.retrieval import RetrievalMetadataFilter, RetrievalRerankOptions
from adaptive_rag.retrieval import RetrievalSearchRequest as ServiceSearchRequest
from adaptive_rag.retrieval.payloads import serialize_retrieval_results
from adaptive_rag.retrieval.service import RetrievalSearchResult as ServiceSearchResult


class RetrievalMetadataFilterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: UUID | None = None
    document_id: UUID | None = None
    source_type: str | None = None
    tags: tuple[str, ...] = ()
    source_created_at_from: datetime | None = None
    source_created_at_to: datetime | None = None
    document_created_at_from: datetime | None = None
    document_created_at_to: datetime | None = None

    def to_service_filter(self) -> RetrievalMetadataFilter:
        return RetrievalMetadataFilter(
            source_id=self.source_id,
            document_id=self.document_id,
            source_type=self.source_type,
            tags=self.tags,
            source_created_at_from=self.source_created_at_from,
            source_created_at_to=self.source_created_at_to,
            document_created_at_from=self.document_created_at_from,
            document_created_at_to=self.document_created_at_to,
        )


class RetrievalRerankRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_limit: int

    def to_service_options(self) -> RetrievalRerankOptions:
        return RetrievalRerankOptions(candidate_limit=self.candidate_limit)


class RetrievalSearchRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    limit: int = 10
    metadata_filter: RetrievalMetadataFilterRequest | None = None
    rerank: RetrievalRerankRequest | None = None

    def validate_rerank_options(self) -> None:
        if self.rerank is None:
            return
        if self.rerank.candidate_limit <= 0:
            raise ValueError("rerank candidate_limit must be positive")
        if self.rerank.candidate_limit < self.limit:
            raise ValueError(
                "rerank candidate_limit must be greater than or equal to limit"
            )

    def to_service_request(self, project_id: UUID) -> ServiceSearchRequest:
        return ServiceSearchRequest(
            project_id=project_id,
            query=self.query,
            limit=self.limit,
            metadata_filter=(
                self.metadata_filter.to_service_filter()
                if self.metadata_filter is not None
                else None
            ),
            rerank=(
                self.rerank.to_service_options() if self.rerank is not None else None
            ),
        )


class RetrievalCitationResponse(BaseModel):
    source_id: UUID
    source_type: str
    source_external_id: str
    source_tags: list[str]
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


class RetrievalResultResponse(BaseModel):
    chunk_id: UUID
    distance: float
    score: float
    citation: RetrievalCitationResponse
    embedding_metadata: dict[str, Any] | None
    rerank_metadata: dict[str, Any] | None = None

    @model_serializer(mode="wrap")
    def serialize(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        payload = handler(self)
        if not isinstance(payload, dict):
            raise TypeError("retrieval result serializer expected a dict")
        if self.rerank_metadata is None:
            payload.pop("rerank_metadata", None)
        return payload


class RetrievalSearchResponse(BaseModel):
    results: list[RetrievalResultResponse]

    @classmethod
    def from_service_results(
        cls,
        results: list[ServiceSearchResult],
    ) -> RetrievalSearchResponse:
        return cls.model_validate({"results": serialize_retrieval_results(results)})
