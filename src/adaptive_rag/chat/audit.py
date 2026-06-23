"""Wiring de audit trail para el servicio de chat."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from adaptive_rag.chat.models import ChatRequest
from adaptive_rag.db.repositories import ChatAuditRepository, ProviderUsageRepository
from adaptive_rag.provider_usage import ProviderCallRecord
from adaptive_rag.retrieval import RetrievalMetadataFilter
from adaptive_rag.retrieval.payloads import RetrievalResultPayload


class ChatAuditWriter(Protocol):
    """Sink inyectable para audit trail de chat."""

    def start_session(
        self,
        request: ChatRequest,
        message: str,
        *,
        model_config_json: Mapping[str, Any] | None = None,
        prompt_version: str | None = None,
    ) -> UUID | None:
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
        strategy: str = "dense",
    ) -> None:
        """Registra una llamada exitosa a la tool de retrieval."""
        ...

    def start_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        strategy: str = "dense",
    ) -> UUID | None:
        """Registra el inicio de una llamada a la tool de retrieval."""
        ...

    def complete_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID,
        tool_call_id: UUID | None,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        latency_ms: int,
        results: Sequence[RetrievalResultPayload],
        strategy: str = "dense",
    ) -> None:
        """Completa una llamada exitosa a la tool de retrieval."""
        ...

    def fail_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID,
        tool_call_id: UUID | None,
        error_message: str,
        latency_ms: int,
    ) -> None:
        """Marca como fallida una llamada iniciada a la tool de retrieval."""
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

    def start_session(
        self,
        request: ChatRequest,
        message: str,
        *,
        model_config_json: Mapping[str, Any] | None = None,
        prompt_version: str | None = None,
    ) -> UUID | None:
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
        strategy: str = "dense",
    ) -> None:
        return None

    def start_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        strategy: str = "dense",
    ) -> UUID | None:
        return None

    def complete_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID,
        tool_call_id: UUID | None,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        latency_ms: int,
        results: Sequence[RetrievalResultPayload],
        strategy: str = "dense",
    ) -> None:
        return None

    def fail_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID,
        tool_call_id: UUID | None,
        error_message: str,
        latency_ms: int,
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

    def start_session(
        self,
        request: ChatRequest,
        message: str,
        *,
        model_config_json: Mapping[str, Any] | None = None,
        prompt_version: str | None = None,
    ) -> UUID | None:
        event: dict[str, object] = {
            "event": "start_session",
            "project_id": str(request.project_id),
            "message": message,
            "retrieval_limit": request.retrieval_limit,
        }
        if model_config_json is not None:
            event["model_config_json"] = dict(model_config_json)
        if prompt_version is not None:
            event["prompt_version"] = prompt_version
        self.events.append(event)
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
        strategy: str = "dense",
    ) -> None:
        self.events.append(
            {
                "event": "retrieval_tool",
                "query": query,
                "limit": limit,
                "strategy": strategy,
                "fallback_reason": _fallback_reason(results),
                "result_count": len(results),
                "chunk_ids": [str(result["chunk_id"]) for result in results],
                "metadata_filter": serialize_metadata_filter(metadata_filter),
                "latency_ms": latency_ms,
            }
        )

    def start_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        strategy: str = "dense",
    ) -> UUID | None:
        return uuid4()

    def complete_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID,
        tool_call_id: UUID | None,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        latency_ms: int,
        results: Sequence[RetrievalResultPayload],
        strategy: str = "dense",
    ) -> None:
        self.record_retrieval_tool(
            project_id,
            session_id,
            query,
            limit,
            metadata_filter,
            latency_ms,
            results,
            strategy,
        )

    def fail_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID,
        tool_call_id: UUID | None,
        error_message: str,
        latency_ms: int,
    ) -> None:
        self.events.append(
            {
                "event": "retrieval_tool_failed",
                "error_message": error_message,
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
        session: Session,
        chat_audit_repository: ChatAuditRepository,
        provider_usage_repository: ProviderUsageRepository,
    ) -> None:
        self._session = session
        self._chat_audit_repository = chat_audit_repository
        self._provider_usage_repository = provider_usage_repository

    def start_session(
        self,
        request: ChatRequest,
        message: str,
        *,
        model_config_json: Mapping[str, Any] | None = None,
        prompt_version: str | None = None,
    ) -> UUID | None:
        chat_session = self._chat_audit_repository.create_session(
            project_id=request.project_id,
            model_config_json=model_config_json,
            prompt_version=prompt_version,
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
        strategy: str = "dense",
    ) -> None:
        if session_id is None:
            return

        tool_call_id = self.start_retrieval_tool(
            project_id,
            session_id,
            query,
            limit,
            metadata_filter,
            strategy,
        )
        self.complete_retrieval_tool(
            project_id,
            session_id,
            tool_call_id,
            query,
            limit,
            metadata_filter,
            latency_ms,
            results,
            strategy,
        )

    def start_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID | None,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        strategy: str = "dense",
    ) -> UUID | None:
        if session_id is None:
            return None

        tool_call = self._chat_audit_repository.start_tool_call(
            project_id=project_id,
            session_id=session_id,
            tool_name="retrieval.search",
            arguments_json={
                "query": query,
                "limit": limit,
                "metadata_filter": serialize_metadata_filter(metadata_filter),
                "strategy": strategy,
            },
        )
        return tool_call.id

    def complete_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID | None,
        tool_call_id: UUID | None,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        latency_ms: int,
        results: Sequence[RetrievalResultPayload],
        strategy: str = "dense",
    ) -> None:
        if session_id is None or tool_call_id is None:
            return

        filters_json = serialize_metadata_filter(metadata_filter)
        self._chat_audit_repository.complete_tool_call(
            project_id=project_id,
            tool_call_id=tool_call_id,
            result_summary_json=_retrieval_result_summary(
                results=results,
                strategy=strategy,
            ),
            latency_ms=latency_ms,
        )
        retrieval_run = self._chat_audit_repository.create_retrieval_run(
            project_id=project_id,
            session_id=session_id,
            tool_call_id=tool_call_id,
            query=query,
            strategy=strategy,
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
                dense_score=_dense_score(result),
                lexical_score=_retrieval_metadata_score(result, "lexical_score"),
                rrf_score=_retrieval_metadata_score(result, "rrf_score"),
                rerank_score=_rerank_score(result),
                citation_json=result["citation"],
            )

    def fail_retrieval_tool(
        self,
        project_id: UUID,
        session_id: UUID | None,
        tool_call_id: UUID | None,
        error_message: str,
        latency_ms: int,
    ) -> None:
        if session_id is None or tool_call_id is None:
            return
        self._chat_audit_repository.fail_tool_call(
            project_id=project_id,
            tool_call_id=tool_call_id,
            error_message=error_message,
            latency_ms=latency_ms,
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
                with self._session.begin_nested():
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


def _retrieval_result_summary(
    *,
    results: Sequence[RetrievalResultPayload],
    strategy: str,
) -> dict[str, object]:
    summary: dict[str, object] = {
        "result_count": len(results),
        "strategy": strategy,
    }
    fallback_reason = _fallback_reason(results)
    if fallback_reason is not None:
        summary["fallback_reason"] = fallback_reason
    return summary


def _fallback_reason(results: Sequence[RetrievalResultPayload]) -> str | None:
    for result in results:
        fallback_reason = result.get("fallback_reason")
        if fallback_reason is not None:
            return fallback_reason
    return None


def _dense_score(result: RetrievalResultPayload) -> float | None:
    metadata_score = _retrieval_metadata_score(result, "dense_score")
    if metadata_score is not None:
        return metadata_score
    if result["strategy"] in {"dense", "graph"}:
        return result["score"]
    return None


def _retrieval_metadata_score(
    result: RetrievalResultPayload,
    key: str,
) -> float | None:
    metadata = result.get("retrieval_metadata")
    if metadata is None:
        return None
    return _numeric_score(metadata.get(key))


def _rerank_score(result: RetrievalResultPayload) -> float | None:
    metadata = result.get("rerank_metadata")
    if metadata is None:
        return None
    return _numeric_score(metadata.get("rerank_score"))


def _numeric_score(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None
