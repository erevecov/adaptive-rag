"""Wiring de audit trail para el servicio de chat."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Protocol
from uuid import UUID, uuid4

from adaptive_rag.chat.models import ChatRequest
from adaptive_rag.provider_usage import ProviderCallRecord
from adaptive_rag.retrieval import RetrievalMetadataFilter
from adaptive_rag.retrieval.payloads import RetrievalResultPayload


class ChatAuditWriter(Protocol):
    """Sink inyectable para audit trail de chat."""

    def start_session(self, request: ChatRequest, message: str) -> UUID | None:
        """Inicia una sesion auditable y devuelve su id cuando existe."""
        ...

    def record_message(
        self,
        project_id: UUID,
        session_id: UUID,
        role: str,
        content: str,
        metadata_json: Mapping[str, Any] | None = None,
    ) -> None:
        """Registra un mensaje de chat."""
        ...

    def record_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        latency_ms: int,
        results: Sequence[RetrievalResultPayload],
    ) -> None:
        """Registra una llamada exitosa a la tool de retrieval."""
        ...

    def succeed_session(self, project_id: UUID, session_id: UUID) -> None:
        """Marca una sesion como exitosa."""
        ...

    def fail_session(
        self,
        project_id: UUID,
        session_id: UUID,
        error_message: str,
    ) -> None:
        """Marca una sesion como fallida."""
        ...

    def record_provider_usage(
        self,
        project_id: UUID,
        session_id: UUID,
        records: Sequence[ProviderCallRecord],
    ) -> None:
        """Registra usage/costo de providers asociado a la sesion."""
        ...


class NullChatAuditWriter:
    """Audit writer no-op para mantener el contrato existente por defecto."""

    def start_session(self, request: ChatRequest, message: str) -> UUID | None:
        return None

    def record_message(
        self,
        project_id: UUID,
        session_id: UUID,
        role: str,
        content: str,
        metadata_json: Mapping[str, Any] | None = None,
    ) -> None:
        return None

    def record_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        latency_ms: int,
        results: Sequence[RetrievalResultPayload],
    ) -> None:
        return None

    def succeed_session(self, project_id: UUID, session_id: UUID) -> None:
        return None

    def fail_session(
        self,
        project_id: UUID,
        session_id: UUID,
        error_message: str,
    ) -> None:
        return None

    def record_provider_usage(
        self,
        project_id: UUID,
        session_id: UUID,
        records: Sequence[ProviderCallRecord],
    ) -> None:
        return None


@dataclass(slots=True)
class InMemoryChatAuditWriter:
    """Audit writer simple para tests de wiring."""

    session_id: UUID = field(default_factory=uuid4)
    events: list[dict[str, object]] = field(default_factory=list)

    def start_session(self, request: ChatRequest, message: str) -> UUID | None:
        self.events.append(
            {
                "event": "start_session",
                "project_id": str(request.project_id),
                "message": message,
                "retrieval_limit": request.retrieval_limit,
            }
        )
        return self.session_id

    def record_message(
        self,
        project_id: UUID,
        session_id: UUID,
        role: str,
        content: str,
        metadata_json: Mapping[str, Any] | None = None,
    ) -> None:
        self.events.append(
            {
                "event": "message",
                "role": role,
                "content": content,
            }
        )

    def record_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        latency_ms: int,
        results: Sequence[RetrievalResultPayload],
    ) -> None:
        self.events.append(
            {
                "event": "retrieval_tool",
                "query": query,
                "limit": limit,
                "result_count": len(results),
                "chunk_ids": [str(result["chunk_id"]) for result in results],
            }
        )

    def succeed_session(self, project_id: UUID, session_id: UUID) -> None:
        self.events.append({"event": "succeed_session"})

    def fail_session(
        self,
        project_id: UUID,
        session_id: UUID,
        error_message: str,
    ) -> None:
        self.events.append(
            {
                "event": "fail_session",
                "error_message": error_message,
            }
        )

    def record_provider_usage(
        self,
        project_id: UUID,
        session_id: UUID,
        records: Sequence[ProviderCallRecord],
    ) -> None:
        if not records:
            return
        self.events.append(
            {
                "event": "provider_usage",
                "records": [record.as_log_extra() for record in records],
            }
        )


def elapsed_ms(start: float) -> int:
    """Devuelve milisegundos transcurridos desde un monotonic start."""

    return max(0, int((monotonic() - start) * 1000))
