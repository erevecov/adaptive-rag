"""Wiring de audit trail para el servicio de chat."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Protocol
from uuid import UUID, uuid4

from adaptive_rag.chat.models import ChatRequest
from adaptive_rag.db.repositories import ChatAuditRepository, ProviderUsageRepository
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
                "metadata_filter": serialize_metadata_filter(metadata_filter),
                "latency_ms": latency_ms,
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


class SqlAlchemyChatAuditWriter:
    """Audit writer durable sobre repositories SQLAlchemy."""

    def __init__(
        self,
        *,
        chat_audit_repository: ChatAuditRepository,
        provider_usage_repository: ProviderUsageRepository,
    ) -> None:
        self._chat_audit_repository = chat_audit_repository
        self._provider_usage_repository = provider_usage_repository

    def start_session(self, request: ChatRequest, message: str) -> UUID | None:
        chat_session = self._chat_audit_repository.create_session(
            project_id=request.project_id,
        )
        return chat_session.id

    def record_message(
        self,
        project_id: UUID,
        session_id: UUID | None,
        role: str,
        content: str,
        metadata_json: Mapping[str, Any] | None = None,
    ) -> None:
        if session_id is None:
            return
        self._chat_audit_repository.add_message(
            project_id=project_id,
            session_id=session_id,
            role=role,
            content=content,
            metadata_json=metadata_json,
        )

    def record_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID | None,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        latency_ms: int,
        results: Sequence[RetrievalResultPayload],
    ) -> None:
        if session_id is None:
            return

        filters_json = serialize_metadata_filter(metadata_filter)
        tool_call = self._chat_audit_repository.start_tool_call(
            project_id=project_id,
            session_id=session_id,
            tool_name="retrieval.search",
            arguments_json={
                "query": query,
                "limit": limit,
                "metadata_filter": filters_json,
            },
        )
        self._chat_audit_repository.complete_tool_call(
            project_id=project_id,
            tool_call_id=tool_call.id,
            result_summary_json={"result_count": len(results)},
            latency_ms=latency_ms,
        )
        retrieval_run = self._chat_audit_repository.create_retrieval_run(
            project_id=project_id,
            session_id=session_id,
            tool_call_id=tool_call.id,
            query=query,
            strategy="dense",
            top_k=limit,
            used_rerank=any("rerank_metadata" in result for result in results),
            filters_json=filters_json,
            latency_ms=latency_ms,
        )
        for rank, result in enumerate(results, start=1):
            self._chat_audit_repository.add_retrieved_chunk(
                project_id=project_id,
                retrieval_run_id=retrieval_run.id,
                chunk_id=UUID(result["chunk_id"]),
                rank=rank,
                dense_score=result["score"],
                lexical_score=None,
                rrf_score=None,
                rerank_score=_rerank_score(result),
                citation_json=result["citation"],
            )

    def succeed_session(self, project_id: UUID, session_id: UUID | None) -> None:
        if session_id is None:
            return
        self._chat_audit_repository.succeed_session(
            project_id=project_id,
            session_id=session_id,
        )

    def fail_session(
        self,
        project_id: UUID,
        session_id: UUID | None,
        error_message: str,
    ) -> None:
        if session_id is None:
            return
        self._chat_audit_repository.fail_session(
            project_id=project_id,
            session_id=session_id,
            error_message=error_message,
        )

    def record_provider_usage(
        self,
        project_id: UUID,
        session_id: UUID | None,
        records: Sequence[ProviderCallRecord],
    ) -> None:
        if session_id is None:
            return
        first_error: Exception | None = None
        for record in records:
            try:
                with self._provider_usage_repository._session.begin_nested():
                    self._provider_usage_repository.create_from_record(
                        project_id=project_id,
                        session_id=session_id,
                        job_id=None,
                        eval_run_id=None,
                        record=record,
                    )
            except Exception as exc:
                if first_error is None:
                    first_error = exc
        if first_error is not None:
            raise first_error


def elapsed_ms(start: float) -> int:
    """Devuelve milisegundos transcurridos desde un monotonic start."""

    return max(0, int((monotonic() - start) * 1000))


def serialize_metadata_filter(
    metadata_filter: RetrievalMetadataFilter | None,
) -> dict[str, object] | None:
    if metadata_filter is None:
        return None

    payload: dict[str, object] = {}
    if metadata_filter.source_id is not None:
        payload["source_id"] = str(metadata_filter.source_id)
    if metadata_filter.document_id is not None:
        payload["document_id"] = str(metadata_filter.document_id)
    if metadata_filter.source_type is not None:
        payload["source_type"] = metadata_filter.source_type
    if metadata_filter.tags:
        payload["tags"] = list(metadata_filter.tags)
    if metadata_filter.source_created_at_from is not None:
        payload["source_created_at_from"] = (
            metadata_filter.source_created_at_from.isoformat()
        )
    if metadata_filter.source_created_at_to is not None:
        payload["source_created_at_to"] = (
            metadata_filter.source_created_at_to.isoformat()
        )
    if metadata_filter.document_created_at_from is not None:
        payload["document_created_at_from"] = (
            metadata_filter.document_created_at_from.isoformat()
        )
    if metadata_filter.document_created_at_to is not None:
        payload["document_created_at_to"] = (
            metadata_filter.document_created_at_to.isoformat()
        )
    return payload


def _serialize_metadata_filter(
    metadata_filter: RetrievalMetadataFilter | None,
) -> dict[str, object] | None:
    return serialize_metadata_filter(metadata_filter)


def _rerank_score(result: RetrievalResultPayload) -> float | None:
    metadata = result.get("rerank_metadata")
    if metadata is None:
        return None
    value = metadata.get("rerank_score")
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None
