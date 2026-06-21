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
    ChatSessionDetail,
    ChatSessionSummary,
    ChatSessionSummaryPage,
)


class ChatRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    retrieval_limit: int = 5
    metadata_filter: RetrievalMetadataFilterRequest | None = None

    def to_service_request(self, project_id: UUID) -> ChatRequest:
        return ChatRequest(
            project_id=project_id,
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
    model_config_: dict[str, Any] | None = Field(alias="model_config")
    prompt_version: str | None
    message_count: int
    tool_call_count: int
    retrieval_run_count: int
    provider_usage_count: int
    total_estimated_cost_usd: float
    error_message: str | None

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
                "model_config": summary.model_config,
                "prompt_version": summary.prompt_version,
                "message_count": summary.message_count,
                "tool_call_count": summary.tool_call_count,
                "retrieval_run_count": summary.retrieval_run_count,
                "provider_usage_count": summary.provider_usage_count,
                "total_estimated_cost_usd": summary.total_estimated_cost_usd,
                "error_message": summary.error_message,
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


class ChatSessionMetadataResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
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
                "model_config": (
                    dict(session.model_config_json)
                    if session.model_config_json is not None
                    else None
                ),
                "prompt_version": session.prompt_version,
                "error_message": session.error_message,
            }
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
