"""Schemas HTTP para la superficie de chat/tool calling."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from adaptive_rag.api.schemas.retrieval import (
    RetrievalMetadataFilterRequest,
    RetrievalResultResponse,
)
from adaptive_rag.chat import ChatRequest
from adaptive_rag.chat.models import ChatResponse as ServiceChatResponse
from adaptive_rag.chat.payloads import serialize_chat_response


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

    @classmethod
    def from_chat_response(
        cls,
        response: ServiceChatResponse,
    ) -> ChatResponseBody:
        return cls.model_validate(serialize_chat_response(response))
