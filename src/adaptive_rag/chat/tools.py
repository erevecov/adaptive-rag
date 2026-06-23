"""Tools disponibles para runners conversacionales."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Protocol
from uuid import UUID

from adaptive_rag.chat.audit import (
    ChatAuditWriter,
    NullChatAuditWriter,
    elapsed_ms,
)
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
        audit_writer: ChatAuditWriter | None = None,
        audit_session_id: UUID | None = None,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._project_id = project_id
        self._default_limit = default_limit
        self._default_metadata_filter = default_metadata_filter
        self._audit_writer = (
            audit_writer if audit_writer is not None else NullChatAuditWriter()
        )
        self._audit_session_id = audit_session_id
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
        start = monotonic()
        audit_tool_call_id = (
            self._audit_writer.start_retrieval_tool(
                self._project_id,
                self._audit_session_id,
                query,
                active_limit,
                active_filter,
            )
            if self._audit_session_id is not None
            else None
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
            if self._audit_session_id is not None:
                self._audit_writer.fail_retrieval_tool(
                    self._project_id,
                    self._audit_session_id,
                    audit_tool_call_id,
                    str(exc),
                    elapsed_ms(start),
                )
            raise ChatServiceError(str(exc)) from exc
        except Exception as exc:
            if self._audit_session_id is not None:
                self._audit_writer.fail_retrieval_tool(
                    self._project_id,
                    self._audit_session_id,
                    audit_tool_call_id,
                    str(exc),
                    elapsed_ms(start),
                )
            raise

        latency_ms = elapsed_ms(start)
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
        if self._audit_session_id is not None:
            self._audit_writer.complete_retrieval_tool(
                self._project_id,
                self._audit_session_id,
                audit_tool_call_id,
                query,
                active_limit,
                active_filter,
                latency_ms,
                payloads,
                _strategy_for_results(results),
            )
        return ChatRetrievalToolResult(results=payloads)


def _strategy_for_results(results: list[RetrievalSearchResult]) -> str:
    if any(result.strategy == "graph" for result in results):
        return "graph"
    if any(result.strategy == "dense_sparse" for result in results):
        return "dense_sparse"
    if any(result.strategy == "hybrid_rrf" for result in results):
        return "hybrid_rrf"
    if any(result.strategy == "lexical" for result in results):
        return "lexical"
    return "dense"
