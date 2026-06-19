"""Servicio compartido de chat/tool calling."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from adaptive_rag.chat.errors import ChatServiceError
from adaptive_rag.chat.models import (
    ChatRequest,
    ChatResponse,
    ChatRunnerOutput,
    ChatRunnerRequest,
)
from adaptive_rag.chat.tools import ChatRetrievalTool, ChatTools, RetrievalSearcher
from adaptive_rag.retrieval.payloads import RetrievalResultPayload


class ChatRunner(Protocol):
    """Runner conversacional inyectable para aislar frameworks agentic."""

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        """Ejecuta una vuelta de chat con tools disponibles."""


class ChatService:
    """Orquesta chat y expone retrieval como tool reutilizable."""

    def __init__(
        self,
        *,
        runner: ChatRunner,
        retrieval_service: RetrievalSearcher,
    ) -> None:
        self._runner = runner
        self._retrieval_service = retrieval_service

    def respond(self, request: ChatRequest) -> ChatResponse:
        message = _validate_message(request.message)
        if request.retrieval_limit <= 0:
            raise ChatServiceError("retrieval_limit must be positive")

        runner_request = ChatRunnerRequest(
            project_id=request.project_id,
            message=message,
            retrieval_limit=request.retrieval_limit,
            metadata_filter=request.metadata_filter,
        )
        retrieval_tool = ChatRetrievalTool(
            retrieval_service=self._retrieval_service,
            project_id=request.project_id,
            default_limit=request.retrieval_limit,
            default_metadata_filter=request.metadata_filter,
        )
        output = self._runner.run(
            runner_request,
            ChatTools(retrieval=retrieval_tool),
        )
        citations = _resolve_citations(
            cited_chunk_ids=output.cited_chunk_ids,
            retrieved_results=retrieval_tool.retrieved_results,
        )
        return ChatResponse(
            answer=output.answer,
            citations=citations,
            tool_calls=retrieval_tool.tool_calls,
        )


def _validate_message(message: str) -> str:
    value = message.strip()
    if not value:
        raise ChatServiceError("message must not be empty")
    return value


def _resolve_citations(
    *,
    cited_chunk_ids: tuple[UUID, ...],
    retrieved_results: dict[UUID, RetrievalResultPayload],
) -> tuple[RetrievalResultPayload, ...]:
    citations: list[RetrievalResultPayload] = []
    for chunk_id in cited_chunk_ids:
        try:
            citations.append(retrieved_results[chunk_id])
        except KeyError as exc:
            raise ChatServiceError(
                f"citation {chunk_id} was not returned by retrieval"
            ) from exc
    return tuple(citations)
