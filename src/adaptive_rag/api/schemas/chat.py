"""Schemas HTTP para la superficie de chat/tool calling."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from adaptive_rag.api.schemas.retrieval import (
    RetrievalMetadataFilterRequest,
    RetrievalResultResponse,
)
from adaptive_rag.chat import ChatRequest
from adaptive_rag.chat.models import ChatResponse as ServiceChatResponse
from adaptive_rag.chat.payloads import serialize_chat_response
from adaptive_rag.db.models import (
    ChatMessage,
    ChatSession,
    ProviderUsage,
    RetrievalRun,
    RetrievedChunk,
    ToolCall,
)
from adaptive_rag.db.repositories import (
    ChatObservabilityErrorMessage,
    ChatObservabilityErrorSummary,
    ChatObservabilityFilters,
    ChatObservabilityLatencySummary,
    ChatObservabilityProviderUsageGroup,
    ChatObservabilityProviderUsageSummary,
    ChatObservabilitySessionSummary,
    ChatObservabilitySummary,
    ChatSessionDetail,
    ChatSessionSummary,
    ChatSessionSummaryPage,
)


class ChatRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    retrieval_limit: int = 5
    metadata_filter: RetrievalMetadataFilterRequest | None = None

    def to_service_request(
        self,
        project_id: UUID,
        *,
        user_id: UUID | None = None,
    ) -> ChatRequest:
        return ChatRequest(
            project_id=project_id,
            user_id=user_id,
            message=self.message,
            retrieval_limit=self.retrieval_limit,
            metadata_filter=(
                self.metadata_filter.to_service_filter()
                if self.metadata_filter is not None
                else None
            ),
        )


class ChatToolCallResponse(BaseModel):
    name: str
    query: str
    limit: int
    result_count: int


class ChatResponseBody(BaseModel):
    answer: str
    citations: list[RetrievalResultResponse]
    tool_calls: list[ChatToolCallResponse]
    session_id: UUID | None = None

    @classmethod
    def from_chat_response(
        cls,
        response: ServiceChatResponse,
    ) -> ChatResponseBody:
        return cls.model_validate(serialize_chat_response(response))


class ChatSessionSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    title: str | None
    title_is_custom: bool
    archived_at: datetime | None
    model_config_: dict[str, Any] | None = Field(alias="model_config")
    prompt_version: str | None
    message_count: int
    tool_call_count: int
    retrieval_run_count: int
    provider_usage_count: int
    total_estimated_cost_usd: float
    error_message: str | None
    has_pending_training: bool
    has_approved_training: bool

    @classmethod
    def from_summary(
        cls,
        summary: ChatSessionSummary,
    ) -> ChatSessionSummaryResponse:
        return cls.model_validate(
            {
                "session_id": summary.session_id,
                "status": summary.status,
                "created_at": summary.created_at,
                "updated_at": summary.updated_at,
                "title": summary.title,
                "title_is_custom": summary.title_is_custom,
                "archived_at": summary.archived_at,
                "model_config": summary.model_config,
                "prompt_version": summary.prompt_version,
                "message_count": summary.message_count,
                "tool_call_count": summary.tool_call_count,
                "retrieval_run_count": summary.retrieval_run_count,
                "provider_usage_count": summary.provider_usage_count,
                "total_estimated_cost_usd": summary.total_estimated_cost_usd,
                "error_message": summary.error_message,
                "has_pending_training": summary.has_pending_training,
                "has_approved_training": summary.has_approved_training,
            }
        )


class ChatSessionListResponse(BaseModel):
    items: list[ChatSessionSummaryResponse]
    next_cursor: str | None

    @classmethod
    def from_summary_page(
        cls,
        page: ChatSessionSummaryPage,
    ) -> ChatSessionListResponse:
        return cls(
            items=[
                ChatSessionSummaryResponse.from_summary(summary)
                for summary in page.items
            ],
            next_cursor=page.next_cursor,
        )


class ChatObservabilityFiltersResponse(BaseModel):
    created_at_from: datetime | None
    created_at_to: datetime | None
    status: str | None

    @classmethod
    def from_filters(
        cls,
        filters: ChatObservabilityFilters,
    ) -> ChatObservabilityFiltersResponse:
        return cls(
            created_at_from=filters.created_at_from,
            created_at_to=filters.created_at_to,
            status=filters.status,
        )


class ChatObservabilitySessionSummaryResponse(BaseModel):
    total: int
    by_status: dict[str, int]

    @classmethod
    def from_summary(
        cls,
        summary: ChatObservabilitySessionSummary,
    ) -> ChatObservabilitySessionSummaryResponse:
        return cls(
            total=summary.total,
            by_status=dict(summary.by_status),
        )


class ChatObservabilityLatencySummaryResponse(BaseModel):
    count: int
    min: int | None
    avg: float | None
    p50: int | None
    p95: int | None
    max: int | None

    @classmethod
    def from_summary(
        cls,
        summary: ChatObservabilityLatencySummary,
    ) -> ChatObservabilityLatencySummaryResponse:
        return cls(
            count=summary.count,
            min=summary.min,
            avg=summary.avg,
            p50=summary.p50,
            p95=summary.p95,
            max=summary.max,
        )


class ChatObservabilityProviderUsageGroupResponse(BaseModel):
    operation: str
    provider: str
    model: str
    record_count: int
    estimated_cost_usd: float | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    input_count: int | None
    latency_ms: ChatObservabilityLatencySummaryResponse

    @classmethod
    def from_group(
        cls,
        group: ChatObservabilityProviderUsageGroup,
    ) -> ChatObservabilityProviderUsageGroupResponse:
        return cls(
            operation=group.operation,
            provider=group.provider,
            model=group.model,
            record_count=group.record_count,
            estimated_cost_usd=group.estimated_cost_usd,
            input_tokens=group.input_tokens,
            output_tokens=group.output_tokens,
            total_tokens=group.total_tokens,
            input_count=group.input_count,
            latency_ms=ChatObservabilityLatencySummaryResponse.from_summary(
                group.latency_ms
            ),
        )


class ChatObservabilityProviderUsageSummaryResponse(BaseModel):
    total_records: int
    total_estimated_cost_usd: float
    missing_cost_count: int
    groups: list[ChatObservabilityProviderUsageGroupResponse]

    @classmethod
    def from_summary(
        cls,
        summary: ChatObservabilityProviderUsageSummary,
    ) -> ChatObservabilityProviderUsageSummaryResponse:
        return cls(
            total_records=summary.total_records,
            total_estimated_cost_usd=summary.total_estimated_cost_usd,
            missing_cost_count=summary.missing_cost_count,
            groups=[
                ChatObservabilityProviderUsageGroupResponse.from_group(group)
                for group in summary.groups
            ],
        )


class ChatObservabilityErrorMessageResponse(BaseModel):
    message: str
    count: int

    @classmethod
    def from_message(
        cls,
        message: ChatObservabilityErrorMessage,
    ) -> ChatObservabilityErrorMessageResponse:
        return cls(message=message.message, count=message.count)


class ChatObservabilityErrorSummaryResponse(BaseModel):
    session_error_count: int
    provider_error_count: int
    top_messages: list[ChatObservabilityErrorMessageResponse]

    @classmethod
    def from_summary(
        cls,
        summary: ChatObservabilityErrorSummary,
    ) -> ChatObservabilityErrorSummaryResponse:
        return cls(
            session_error_count=summary.session_error_count,
            provider_error_count=summary.provider_error_count,
            top_messages=[
                ChatObservabilityErrorMessageResponse.from_message(message)
                for message in summary.top_messages
            ],
        )


class ChatObservabilitySummaryResponse(BaseModel):
    project_id: UUID
    filters: ChatObservabilityFiltersResponse
    sessions: ChatObservabilitySessionSummaryResponse
    provider_usage: ChatObservabilityProviderUsageSummaryResponse
    errors: ChatObservabilityErrorSummaryResponse

    @classmethod
    def from_summary(
        cls,
        summary: ChatObservabilitySummary,
    ) -> ChatObservabilitySummaryResponse:
        return cls(
            project_id=summary.project_id,
            filters=ChatObservabilityFiltersResponse.from_filters(summary.filters),
            sessions=ChatObservabilitySessionSummaryResponse.from_summary(
                summary.sessions
            ),
            provider_usage=ChatObservabilityProviderUsageSummaryResponse.from_summary(
                summary.provider_usage
            ),
            errors=ChatObservabilityErrorSummaryResponse.from_summary(summary.errors),
        )


class ChatSessionMetadataResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    title: str | None
    title_is_custom: bool
    archived_at: datetime | None
    model_config_: dict[str, Any] | None = Field(alias="model_config")
    prompt_version: str | None
    error_message: str | None

    @classmethod
    def from_session(
        cls,
        session: ChatSession,
    ) -> ChatSessionMetadataResponse:
        return cls.model_validate(
            {
                "session_id": session.id,
                "status": session.status,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "title": session.title,
                "title_is_custom": session.title_is_custom,
                "archived_at": session.archived_at,
                "model_config": (
                    dict(session.model_config_json)
                    if session.model_config_json is not None
                    else None
                ),
                "prompt_version": session.prompt_version,
                "error_message": session.error_message,
            }
        )


class ChatSessionTitleUpdateBody(BaseModel):
    title: str = Field(min_length=1, max_length=60)


class ChatSessionTitleUpdateResponse(BaseModel):
    session_id: UUID
    title: str
    title_is_custom: bool

    @classmethod
    def from_session(
        cls,
        session: ChatSession,
    ) -> ChatSessionTitleUpdateResponse:
        return cls(
            session_id=session.id,
            title=session.title or "",
            title_is_custom=session.title_is_custom,
        )


class ChatHistoryMessageResponse(BaseModel):
    message_id: UUID
    role: str
    content: str
    metadata: dict[str, Any] | None
    created_at: datetime

    @classmethod
    def from_message(
        cls,
        message: ChatMessage,
    ) -> ChatHistoryMessageResponse:
        return cls(
            message_id=message.id,
            role=message.role,
            content=message.content,
            metadata=(
                dict(message.metadata_json)
                if message.metadata_json is not None
                else None
            ),
            created_at=message.created_at,
        )


class ChatHistoryToolCallResponse(BaseModel):
    tool_call_id: UUID
    tool_name: str
    arguments: dict[str, Any] | None
    result_summary: dict[str, Any] | None
    status: str
    latency_ms: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_tool_call(
        cls,
        tool_call: ToolCall,
    ) -> ChatHistoryToolCallResponse:
        return cls(
            tool_call_id=tool_call.id,
            tool_name=tool_call.tool_name,
            arguments=(
                dict(tool_call.arguments_json)
                if tool_call.arguments_json is not None
                else None
            ),
            result_summary=(
                dict(tool_call.result_summary_json)
                if tool_call.result_summary_json is not None
                else None
            ),
            status=tool_call.status,
            latency_ms=tool_call.latency_ms,
            error_message=tool_call.error_message,
            created_at=tool_call.created_at,
            updated_at=tool_call.updated_at,
        )


class ChatHistoryRetrievedChunkResponse(BaseModel):
    retrieved_chunk_id: UUID
    chunk_id: UUID
    rank: int
    dense_score: float | None
    lexical_score: float | None
    sparse_score: float | None
    rrf_score: float | None
    rerank_score: float | None
    citation: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_retrieved_chunk(
        cls,
        retrieved_chunk: RetrievedChunk,
    ) -> ChatHistoryRetrievedChunkResponse:
        return cls(
            retrieved_chunk_id=retrieved_chunk.id,
            chunk_id=retrieved_chunk.chunk_id,
            rank=retrieved_chunk.rank,
            dense_score=retrieved_chunk.dense_score,
            lexical_score=retrieved_chunk.lexical_score,
            sparse_score=retrieved_chunk.sparse_score,
            rrf_score=retrieved_chunk.rrf_score,
            rerank_score=retrieved_chunk.rerank_score,
            citation=dict(retrieved_chunk.citation_json),
            created_at=retrieved_chunk.created_at,
        )


class ChatHistoryRetrievalRunResponse(BaseModel):
    retrieval_run_id: UUID
    tool_call_id: UUID | None
    query: str
    strategy: str
    top_k: int
    used_rerank: bool
    filters: dict[str, Any] | None
    latency_ms: int | None
    error_message: str | None
    created_at: datetime
    retrieved_chunks: list[ChatHistoryRetrievedChunkResponse]

    @classmethod
    def from_retrieval_run(
        cls,
        retrieval_run: RetrievalRun,
        *,
        retrieved_chunks: Sequence[RetrievedChunk],
    ) -> ChatHistoryRetrievalRunResponse:
        return cls(
            retrieval_run_id=retrieval_run.id,
            tool_call_id=retrieval_run.tool_call_id,
            query=retrieval_run.query,
            strategy=retrieval_run.strategy,
            top_k=retrieval_run.top_k,
            used_rerank=retrieval_run.used_rerank,
            filters=(
                dict(retrieval_run.filters_json)
                if retrieval_run.filters_json is not None
                else None
            ),
            latency_ms=retrieval_run.latency_ms,
            error_message=retrieval_run.error_message,
            created_at=retrieval_run.created_at,
            retrieved_chunks=[
                ChatHistoryRetrievedChunkResponse.from_retrieved_chunk(chunk)
                for chunk in retrieved_chunks
            ],
        )


class ChatHistoryProviderUsageResponse(BaseModel):
    provider_usage_id: UUID
    operation: str
    provider: str
    model: str
    status: str
    usage_source: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    input_count: int | None
    estimated_cost_usd: float | None
    currency: str | None
    latency_ms: int | None
    provider_request_id: str | None
    error_message: str | None
    created_at: datetime

    @classmethod
    def from_provider_usage(
        cls,
        usage: ProviderUsage,
    ) -> ChatHistoryProviderUsageResponse:
        return cls(
            provider_usage_id=usage.id,
            operation=usage.operation,
            provider=usage.provider,
            model=usage.model,
            status=usage.status,
            usage_source=usage.usage_source,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            input_count=usage.input_count,
            estimated_cost_usd=usage.estimated_cost_usd,
            currency=usage.currency,
            latency_ms=usage.latency_ms,
            provider_request_id=usage.provider_request_id,
            error_message=usage.error_message,
            created_at=usage.created_at,
        )


class ChatSessionDetailResponse(BaseModel):
    session: ChatSessionMetadataResponse
    messages: list[ChatHistoryMessageResponse]
    tool_calls: list[ChatHistoryToolCallResponse]
    retrieval_runs: list[ChatHistoryRetrievalRunResponse]
    provider_usage: list[ChatHistoryProviderUsageResponse]

    @classmethod
    def from_detail(
        cls,
        detail: ChatSessionDetail,
    ) -> ChatSessionDetailResponse:
        return cls(
            session=ChatSessionMetadataResponse.from_session(detail.session),
            messages=[
                ChatHistoryMessageResponse.from_message(message)
                for message in detail.messages
            ],
            tool_calls=[
                ChatHistoryToolCallResponse.from_tool_call(tool_call)
                for tool_call in detail.tool_calls
            ],
            retrieval_runs=[
                ChatHistoryRetrievalRunResponse.from_retrieval_run(
                    retrieval_run,
                    retrieved_chunks=detail.retrieved_chunks_by_run_id[
                        retrieval_run.id
                    ],
                )
                for retrieval_run in detail.retrieval_runs
            ],
            provider_usage=[
                ChatHistoryProviderUsageResponse.from_provider_usage(usage)
                for usage in detail.provider_usage
            ],
        )
