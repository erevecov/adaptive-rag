"""Tools disponibles para runners conversacionales."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from adaptive_rag.chat.errors import ChatServiceError
from adaptive_rag.chat.models import ChatToolCall
from adaptive_rag.retrieval import (
    RetrievalMetadataFilter,
    RetrievalSearchRequest,
    RetrievalSearchResult,
    RetrievalServiceError,
)
from adaptive_rag.retrieval.payloads import (
    RetrievalResultPayload,
    serialize_retrieval_results,
)


class RetrievalSearcher(Protocol):
    """Parte de RetrievalService que chat necesita reutilizar."""

    def search(
        self,
        request: RetrievalSearchRequest,
    ) -> list[RetrievalSearchResult]:
        """Ejecuta retrieval sobre query text."""


@dataclass(frozen=True, slots=True)
class ChatRetrievalToolResult:
    """Resultado serializable de la tool de retrieval."""

    results: tuple[RetrievalResultPayload, ...]


@dataclass(frozen=True, slots=True)
class ChatTools:
    """Contenedor de tools entregadas al runner conversacional."""

    retrieval: ChatRetrievalTool


class ChatRetrievalTool:
    """Tool que delega retrieval al servicio M4."""

    name = "retrieval.search"

    def __init__(
        self,
        *,
        retrieval_service: RetrievalSearcher,
        project_id: UUID,
        default_limit: int,
        default_metadata_filter: RetrievalMetadataFilter | None,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._project_id = project_id
        self._default_limit = default_limit
        self._default_metadata_filter = default_metadata_filter
        self._tool_calls: list[ChatToolCall] = []
        self._retrieved_results: dict[UUID, RetrievalResultPayload] = {}

    @property
    def tool_calls(self) -> tuple[ChatToolCall, ...]:
        return tuple(self._tool_calls)

    @property
    def retrieved_results(self) -> dict[UUID, RetrievalResultPayload]:
        return dict(self._retrieved_results)

    def search(
        self,
        *,
        query: str,
        limit: int | None = None,
        metadata_filter: RetrievalMetadataFilter | None = None,
    ) -> ChatRetrievalToolResult:
        active_limit = self._default_limit if limit is None else limit
        active_filter = (
            self._default_metadata_filter
            if metadata_filter is None
            else metadata_filter
        )
        try:
            results = self._retrieval_service.search(
                RetrievalSearchRequest(
                    project_id=self._project_id,
                    query=query,
                    limit=active_limit,
                    metadata_filter=active_filter,
                )
            )
        except RetrievalServiceError as exc:
            raise ChatServiceError(str(exc)) from exc

        payloads = tuple(serialize_retrieval_results(results))
        for result, payload in zip(results, payloads, strict=True):
            self._retrieved_results[result.chunk_id] = payload
        self._tool_calls.append(
            ChatToolCall(
                name=self.name,
                query=query,
                limit=active_limit,
                result_count=len(payloads),
            )
        )
        return ChatRetrievalToolResult(results=payloads)
