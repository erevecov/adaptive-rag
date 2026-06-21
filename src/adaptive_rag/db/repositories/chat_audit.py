"""Repositories para audit trail durable de chat."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import (
    ChatMessage,
    ChatSession,
    Chunk,
    Document,
    DocumentVersion,
    Job,
    ProviderUsage,
    RetrievalRun,
    RetrievedChunk,
    ToolCall,
)
from adaptive_rag.provider_usage import ProviderCallRecord


class ChatAuditRepository:
    """Acceso a audit trail de chat con pertenencia de proyecto explicita."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_session(
        self,
        *,
        project_id: UUID,
        model_config_json: Mapping[str, Any] | None = None,
        prompt_version: str | None = None,
    ) -> ChatSession:
        chat_session = ChatSession(
            project_id=project_id,
            model_config_json=(
                dict(model_config_json) if model_config_json is not None else None
            ),
            prompt_version=prompt_version,
        )
        self._session.add(chat_session)
        self._session.flush()
        return chat_session

    def get_session(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
    ) -> ChatSession | None:
        statement = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.project_id == project_id,
        )
        return self._session.scalars(statement).one_or_none()

    def add_message(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
        role: str,
        content: str,
        metadata_json: Mapping[str, Any] | None = None,
    ) -> ChatMessage:
        self._require_session(project_id=project_id, session_id=session_id)
        message = ChatMessage(
            project_id=project_id,
            session_id=session_id,
            role=role,
            content=content,
            metadata_json=dict(metadata_json) if metadata_json is not None else None,
        )
        self._session.add(message)
        self._session.flush()
        return message

    def list_messages(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
    ) -> list[ChatMessage]:
        statement = (
            select(ChatMessage)
            .where(
                ChatMessage.project_id == project_id,
                ChatMessage.session_id == session_id,
            )
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
        return list(self._session.scalars(statement))

    def succeed_session(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
    ) -> ChatSession:
        chat_session = self._require_session(
            project_id=project_id,
            session_id=session_id,
        )
        chat_session.status = "succeeded"
        chat_session.error_message = None
        self._session.flush()
        return chat_session

    def fail_session(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
        error_message: str,
    ) -> ChatSession:
        chat_session = self._require_session(
            project_id=project_id,
            session_id=session_id,
        )
        chat_session.status = "failed"
        chat_session.error_message = error_message
        self._session.flush()
        return chat_session

    def start_tool_call(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
        tool_name: str,
        arguments_json: Mapping[str, Any] | None = None,
    ) -> ToolCall:
        self._require_session(project_id=project_id, session_id=session_id)
        tool_call = ToolCall(
            project_id=project_id,
            session_id=session_id,
            tool_name=tool_name,
            arguments_json=dict(arguments_json) if arguments_json is not None else None,
        )
        self._session.add(tool_call)
        self._session.flush()
        return tool_call

    def complete_tool_call(
        self,
        *,
        project_id: UUID,
        tool_call_id: UUID,
        result_summary_json: Mapping[str, Any],
        latency_ms: int,
    ) -> ToolCall:
        tool_call = self._require_tool_call(
            project_id=project_id,
            tool_call_id=tool_call_id,
        )
        tool_call.status = "succeeded"
        tool_call.result_summary_json = dict(result_summary_json)
        tool_call.latency_ms = latency_ms
        tool_call.error_message = None
        self._session.flush()
        return tool_call

    def fail_tool_call(
        self,
        *,
        project_id: UUID,
        tool_call_id: UUID,
        error_message: str,
        latency_ms: int,
    ) -> ToolCall:
        tool_call = self._require_tool_call(
            project_id=project_id,
            tool_call_id=tool_call_id,
        )
        tool_call.status = "failed"
        tool_call.error_message = error_message
        tool_call.latency_ms = latency_ms
        self._session.flush()
        return tool_call

    def list_tool_calls(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
    ) -> list[ToolCall]:
        statement = (
            select(ToolCall)
            .where(
                ToolCall.project_id == project_id,
                ToolCall.session_id == session_id,
            )
            .order_by(ToolCall.created_at, ToolCall.id)
        )
        return list(self._session.scalars(statement))

    def create_retrieval_run(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
        tool_call_id: UUID | None,
        query: str,
        strategy: str,
        top_k: int,
        used_rerank: bool,
        filters_json: Mapping[str, Any] | None = None,
        latency_ms: int | None = None,
    ) -> RetrievalRun:
        self._require_session(project_id=project_id, session_id=session_id)
        if tool_call_id is not None:
            self._require_tool_call(
                project_id=project_id,
                tool_call_id=tool_call_id,
                session_id=session_id,
            )

        retrieval_run = RetrievalRun(
            project_id=project_id,
            session_id=session_id,
            tool_call_id=tool_call_id,
            query=query,
            strategy=strategy,
            top_k=top_k,
            used_rerank=used_rerank,
            filters_json=dict(filters_json) if filters_json is not None else None,
            latency_ms=latency_ms,
        )
        self._session.add(retrieval_run)
        self._session.flush()
        return retrieval_run

    def list_retrieval_runs(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
    ) -> list[RetrievalRun]:
        statement = (
            select(RetrievalRun)
            .where(
                RetrievalRun.project_id == project_id,
                RetrievalRun.session_id == session_id,
            )
            .order_by(RetrievalRun.created_at, RetrievalRun.id)
        )
        return list(self._session.scalars(statement))

    def add_retrieved_chunk(
        self,
        *,
        project_id: UUID,
        retrieval_run_id: UUID,
        chunk_id: UUID,
        rank: int,
        citation_json: Mapping[str, Any],
        dense_score: float | None = None,
        lexical_score: float | None = None,
        rrf_score: float | None = None,
        rerank_score: float | None = None,
    ) -> RetrievedChunk:
        self._require_retrieval_run(
            project_id=project_id,
            retrieval_run_id=retrieval_run_id,
        )
        if not self._chunk_belongs_to_project(
            project_id=project_id,
            chunk_id=chunk_id,
        ):
            raise ValueError("chunk does not belong to project")

        retrieved_chunk = RetrievedChunk(
            project_id=project_id,
            retrieval_run_id=retrieval_run_id,
            chunk_id=chunk_id,
            rank=rank,
            dense_score=dense_score,
            lexical_score=lexical_score,
            rrf_score=rrf_score,
            rerank_score=rerank_score,
            citation_json=dict(citation_json),
        )
        self._session.add(retrieved_chunk)
        self._session.flush()
        return retrieved_chunk

    def list_retrieved_chunks(
        self,
        *,
        project_id: UUID,
        retrieval_run_id: UUID,
    ) -> list[RetrievedChunk]:
        statement = (
            select(RetrievedChunk)
            .where(
                RetrievedChunk.project_id == project_id,
                RetrievedChunk.retrieval_run_id == retrieval_run_id,
            )
            .order_by(RetrievedChunk.rank)
        )
        return list(self._session.scalars(statement))

    def _require_session(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
    ) -> ChatSession:
        chat_session = self.get_session(project_id=project_id, session_id=session_id)
        if chat_session is None:
            raise ValueError("chat session does not belong to project")
        return chat_session

    def _require_tool_call(
        self,
        *,
        project_id: UUID,
        tool_call_id: UUID,
        session_id: UUID | None = None,
    ) -> ToolCall:
        statement = select(ToolCall).where(
            ToolCall.id == tool_call_id,
            ToolCall.project_id == project_id,
        )
        tool_call = self._session.scalars(statement).one_or_none()
        if tool_call is None:
            raise ValueError("tool call does not belong to project")
        if session_id is not None and tool_call.session_id != session_id:
            raise ValueError("tool call does not belong to session")
        return tool_call

    def _require_retrieval_run(
        self,
        *,
        project_id: UUID,
        retrieval_run_id: UUID,
    ) -> RetrievalRun:
        statement = select(RetrievalRun).where(
            RetrievalRun.id == retrieval_run_id,
            RetrievalRun.project_id == project_id,
        )
        retrieval_run = self._session.scalars(statement).one_or_none()
        if retrieval_run is None:
            raise ValueError("retrieval run does not belong to project")
        return retrieval_run

    def _chunk_belongs_to_project(
        self,
        *,
        project_id: UUID,
        chunk_id: UUID,
    ) -> bool:
        statement = (
            select(Chunk.id)
            .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(
                Chunk.id == chunk_id,
                Document.project_id == project_id,
            )
        )
        return self._session.scalar(statement) is not None


class ProviderUsageRepository:
    """Acceso a eventos de usage/costo de providers."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_from_record(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        job_id: UUID | None,
        eval_run_id: UUID | None,
        record: ProviderCallRecord,
    ) -> ProviderUsage:
        if session_id is not None:
            self._require_session(project_id=project_id, session_id=session_id)
        if job_id is not None:
            self._require_job(project_id=project_id, job_id=job_id)

        usage = ProviderUsage(
            project_id=project_id,
            session_id=session_id,
            job_id=job_id,
            eval_run_id=eval_run_id,
            operation=record.operation,
            provider=record.provider,
            model=record.model,
            status=record.outcome,
            usage_source=record.usage_source,
            input_tokens=record.usage.input_tokens,
            output_tokens=record.usage.output_tokens,
            total_tokens=record.usage.total_tokens,
            input_count=record.usage.input_count,
            estimated_cost_usd=record.estimated_cost_usd,
            currency="USD" if record.estimated_cost_usd is not None else None,
            latency_ms=record.duration_ms,
            provider_request_id=record.request_id,
            error_message=record.error_type,
        )
        self._session.add(usage)
        self._session.flush()
        return usage

    def _require_session(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
    ) -> ChatSession:
        statement = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.project_id == project_id,
        )
        chat_session = self._session.scalars(statement).one_or_none()
        if chat_session is None:
            raise ValueError("chat session does not belong to project")
        return chat_session

    def _require_job(
        self,
        *,
        project_id: UUID,
        job_id: UUID,
    ) -> Job:
        statement = select(Job).where(
            Job.id == job_id,
            Job.project_id == project_id,
        )
        job = self._session.scalars(statement).one_or_none()
        if job is None:
            raise ValueError("job does not belong to project")
        return job
