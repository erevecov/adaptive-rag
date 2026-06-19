"""Modelos internos del contrato de chat/tool calling."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from adaptive_rag.retrieval import RetrievalMetadataFilter
from adaptive_rag.retrieval.payloads import RetrievalResultPayload


@dataclass(frozen=True, slots=True)
class ChatRequest:
    """Solicitud interna de chat sobre un proyecto."""

    project_id: UUID
    message: str
    retrieval_limit: int = 5
    metadata_filter: RetrievalMetadataFilter | None = None


@dataclass(frozen=True, slots=True)
class ChatRunnerRequest:
    """Request normalizada entregada al runner conversacional."""

    project_id: UUID
    message: str
    retrieval_limit: int
    metadata_filter: RetrievalMetadataFilter | None


@dataclass(frozen=True, slots=True)
class ChatRunnerOutput:
    """Salida estructurada minima devuelta por el runner conversacional."""

    answer: str
    cited_chunk_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True, slots=True)
class ChatToolCall:
    """Metadata minima de una llamada a tool ejecutada durante chat."""

    name: str
    query: str
    limit: int
    result_count: int


@dataclass(frozen=True, slots=True)
class ChatResponse:
    """Respuesta conversacional serializable por futuras superficies API/CLI."""

    answer: str
    citations: tuple[RetrievalResultPayload, ...]
    tool_calls: tuple[ChatToolCall, ...]
