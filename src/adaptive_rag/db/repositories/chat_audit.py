"""Repositories para audit trail durable de chat."""

from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import (
    CHAT_SESSION_STATUS_VALUES,
    ChatMessage,
    ChatSession,
    Chunk,
    Document,
    DocumentVersion,
    Job,
    KnowledgeProposal,
    ProviderUsage,
    RetrievalRun,
    RetrievedChunk,
    ToolCall,
)
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.provider_usage import ProviderCallRecord

DEFAULT_CHAT_SESSION_HISTORY_LIMIT = 20
MAX_CHAT_SESSION_HISTORY_LIMIT = 100
SESSION_TITLE_MAX_LENGTH = 60


@dataclass(frozen=True)
class ChatSessionSummary:
    """Resumen read-only de una sesion de chat persistida."""

    session_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    title: str | None
    title_is_custom: bool
    archived_at: datetime | None
    model_config: dict[str, Any] | None
    prompt_version: str | None
    message_count: int
    tool_call_count: int
    retrieval_run_count: int
    provider_usage_count: int
    total_estimated_cost_usd: float
    error_message: str | None
    has_pending_training: bool
    has_approved_training: bool


@dataclass(frozen=True)
class ChatSessionSummaryPage:
    """Pagina acotada de resumenes de sesiones de chat."""

    items: tuple[ChatSessionSummary, ...]
    next_cursor: str | None


@dataclass(frozen=True)
class ChatSessionDetail:
    """Detalle read-only del audit trail de una sesion de chat."""

    session: ChatSession
    messages: tuple[ChatMessage, ...]
    tool_calls: tuple[ToolCall, ...]
    retrieval_runs: tuple[RetrievalRun, ...]
    retrieved_chunks_by_run_id: Mapping[UUID, tuple[RetrievedChunk, ...]]
    provider_usage: tuple[ProviderUsage, ...]


class ChatAuditRepository:
    """Acceso a audit trail de chat con pertenencia de proyecto explicita."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_session(
        self,
        *,
        project_id: UUID,
        user_id: UUID | None = None,
        model_config_json: Mapping[str, Any] | None = None,
        prompt_version: str | None = None,
    ) -> ChatSession:
        chat_session = ChatSession(
            project_id=project_id,
            user_id=user_id,
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
        user_id: UUID | None = None,
    ) -> ChatSession | None:
        statement = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.project_id == project_id,
        )
        if user_id is not None:
            statement = statement.where(ChatSession.user_id == user_id)
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

    def update_session_title(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
        title: str,
        user_id: UUID | None = None,
    ) -> ChatSession:
        chat_session = self.get_session(
            project_id=project_id,
            session_id=session_id,
            user_id=user_id,
        )
        if chat_session is None:
            raise ValueError("chat session does not belong to project")
        chat_session.title = _normalize_session_title(title)
        chat_session.title_is_custom = True
        self._session.flush()
        return chat_session

    def archive_session(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
        user_id: UUID | None = None,
    ) -> ChatSession:
        chat_session = self.get_session(
            project_id=project_id,
            session_id=session_id,
            user_id=user_id,
        )
        if chat_session is None:
            raise ValueError("chat session does not belong to project")
        if chat_session.archived_at is None:
            chat_session.archived_at = utc_now()
        self._session.flush()
        return chat_session

    def unarchive_session(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
        user_id: UUID | None = None,
    ) -> ChatSession:
        chat_session = self.get_session(
            project_id=project_id,
            session_id=session_id,
            user_id=user_id,
        )
        if chat_session is None:
            raise ValueError("chat session does not belong to project")
        chat_session.archived_at = None
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
        sparse_score: float | None = None,
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
            sparse_score=sparse_score,
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

    def list_session_summaries(
        self,
        *,
        project_id: UUID,
        user_id: UUID | None = None,
        status: str | None = None,
        archived: bool = False,
        limit: int = DEFAULT_CHAT_SESSION_HISTORY_LIMIT,
        cursor: str | None = None,
    ) -> ChatSessionSummaryPage:
        if limit < 1 or limit > MAX_CHAT_SESSION_HISTORY_LIMIT:
            raise ValueError(
                f"limit must be between 1 and {MAX_CHAT_SESSION_HISTORY_LIMIT}"
            )
        if status is not None and status not in CHAT_SESSION_STATUS_VALUES:
            raise ValueError("invalid chat session status")

        cursor_values = _decode_chat_session_cursor(cursor)
        message_count = (
            select(func.count(ChatMessage.id))
            .where(
                ChatMessage.project_id == project_id,
                ChatMessage.session_id == ChatSession.id,
            )
            .correlate(ChatSession)
            .scalar_subquery()
        )
        first_user_message = (
            select(ChatMessage.content)
            .where(
                ChatMessage.project_id == project_id,
                ChatMessage.session_id == ChatSession.id,
                ChatMessage.role == "user",
            )
            .order_by(ChatMessage.created_at, ChatMessage.id)
            .limit(1)
            .correlate(ChatSession)
            .scalar_subquery()
        )
        tool_call_count = (
            select(func.count(ToolCall.id))
            .where(
                ToolCall.project_id == project_id,
                ToolCall.session_id == ChatSession.id,
            )
            .correlate(ChatSession)
            .scalar_subquery()
        )
        retrieval_run_count = (
            select(func.count(RetrievalRun.id))
            .where(
                RetrievalRun.project_id == project_id,
                RetrievalRun.session_id == ChatSession.id,
            )
            .correlate(ChatSession)
            .scalar_subquery()
        )
        provider_usage_count = (
            select(func.count(ProviderUsage.id))
            .where(
                ProviderUsage.project_id == project_id,
                ProviderUsage.session_id == ChatSession.id,
            )
            .correlate(ChatSession)
            .scalar_subquery()
        )
        total_estimated_cost = (
            select(func.coalesce(func.sum(ProviderUsage.estimated_cost_usd), 0.0))
            .where(
                ProviderUsage.project_id == project_id,
                ProviderUsage.session_id == ChatSession.id,
            )
            .correlate(ChatSession)
            .scalar_subquery()
        )
        pending_training_count = (
            select(func.count(KnowledgeProposal.id))
            .where(
                KnowledgeProposal.project_id == project_id,
                KnowledgeProposal.origin_session_id == ChatSession.id,
                KnowledgeProposal.status == "pending",
            )
            .correlate(ChatSession)
            .scalar_subquery()
        )
        approved_training_count = (
            select(func.count(KnowledgeProposal.id))
            .where(
                KnowledgeProposal.project_id == project_id,
                KnowledgeProposal.origin_session_id == ChatSession.id,
                KnowledgeProposal.status == "approved",
            )
            .correlate(ChatSession)
            .scalar_subquery()
        )

        statement = (
            select(
                ChatSession,
                first_user_message,
                message_count,
                tool_call_count,
                retrieval_run_count,
                provider_usage_count,
                total_estimated_cost,
                pending_training_count,
                approved_training_count,
            )
            .where(ChatSession.project_id == project_id)
            .order_by(ChatSession.created_at.desc(), ChatSession.id.desc())
            .limit(limit + 1)
        )
        if archived:
            statement = statement.where(ChatSession.archived_at.is_not(None))
        else:
            statement = statement.where(ChatSession.archived_at.is_(None))
        if user_id is not None:
            statement = statement.where(ChatSession.user_id == user_id)
        if status is not None:
            statement = statement.where(ChatSession.status == status)
        if cursor_values is not None:
            cursor_created_at, cursor_session_id = cursor_values
            statement = statement.where(
                or_(
                    ChatSession.created_at < cursor_created_at,
                    and_(
                        ChatSession.created_at == cursor_created_at,
                        ChatSession.id < cursor_session_id,
                    ),
                )
            )

        rows = self._session.execute(statement).all()
        items = tuple(
            ChatSessionSummary(
                session_id=chat_session.id,
                status=chat_session.status,
                created_at=chat_session.created_at,
                updated_at=chat_session.updated_at,
                title=(
                    chat_session.title
                    if chat_session.title is not None
                    else _derived_session_title(first_user_message_value)
                ),
                title_is_custom=chat_session.title_is_custom,
                archived_at=chat_session.archived_at,
                model_config=(
                    dict(chat_session.model_config_json)
                    if chat_session.model_config_json is not None
                    else None
                ),
                prompt_version=chat_session.prompt_version,
                message_count=int(message_count_value),
                tool_call_count=int(tool_call_count_value),
                retrieval_run_count=int(retrieval_run_count_value),
                provider_usage_count=int(provider_usage_count_value),
                total_estimated_cost_usd=float(total_estimated_cost_value or 0.0),
                error_message=chat_session.error_message,
                has_pending_training=int(pending_training_count_value) > 0,
                has_approved_training=int(approved_training_count_value) > 0,
            )
            for (
                chat_session,
                first_user_message_value,
                message_count_value,
                tool_call_count_value,
                retrieval_run_count_value,
                provider_usage_count_value,
                total_estimated_cost_value,
                pending_training_count_value,
                approved_training_count_value,
            ) in rows[:limit]
        )
        next_cursor = (
            _encode_chat_session_cursor(
                created_at=items[-1].created_at,
                session_id=items[-1].session_id,
            )
            if len(rows) > limit and items
            else None
        )
        return ChatSessionSummaryPage(items=items, next_cursor=next_cursor)

    def get_session_detail(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
        user_id: UUID | None = None,
    ) -> ChatSessionDetail | None:
        chat_session = self.get_session(
            project_id=project_id,
            session_id=session_id,
            user_id=user_id,
        )
        if chat_session is None:
            return None

        messages = tuple(
            self._session.scalars(
                select(ChatMessage)
                .where(
                    ChatMessage.project_id == project_id,
                    ChatMessage.session_id == session_id,
                )
                .order_by(ChatMessage.created_at, ChatMessage.id)
            )
        )
        tool_calls = tuple(
            self._session.scalars(
                select(ToolCall)
                .where(
                    ToolCall.project_id == project_id,
                    ToolCall.session_id == session_id,
                )
                .order_by(ToolCall.created_at, ToolCall.id)
            )
        )
        retrieval_runs = tuple(
            self._session.scalars(
                select(RetrievalRun)
                .where(
                    RetrievalRun.project_id == project_id,
                    RetrievalRun.session_id == session_id,
                )
                .order_by(RetrievalRun.created_at, RetrievalRun.id)
            )
        )
        retrieved_chunks_by_run_id: dict[UUID, tuple[RetrievedChunk, ...]] = {
            retrieval_run.id: ()
            for retrieval_run in retrieval_runs
        }
        if retrieval_runs:
            retrieval_run_ids = [retrieval_run.id for retrieval_run in retrieval_runs]
            retrieved_chunks = self._session.scalars(
                select(RetrievedChunk)
                .where(
                    RetrievedChunk.project_id == project_id,
                    RetrievedChunk.retrieval_run_id.in_(retrieval_run_ids),
                )
                .order_by(RetrievedChunk.retrieval_run_id, RetrievedChunk.rank)
            )
            grouped_chunks: dict[UUID, list[RetrievedChunk]] = {
                retrieval_run.id: [] for retrieval_run in retrieval_runs
            }
            for retrieved_chunk in retrieved_chunks:
                grouped_chunks[retrieved_chunk.retrieval_run_id].append(
                    retrieved_chunk
                )
            retrieved_chunks_by_run_id = {
                retrieval_run_id: tuple(chunks)
                for retrieval_run_id, chunks in grouped_chunks.items()
            }

        provider_usage = tuple(
            self._session.scalars(
                select(ProviderUsage)
                .where(
                    ProviderUsage.project_id == project_id,
                    ProviderUsage.session_id == session_id,
                )
                .order_by(ProviderUsage.created_at, ProviderUsage.id)
            )
        )
        return ChatSessionDetail(
            session=chat_session,
            messages=messages,
            tool_calls=tool_calls,
            retrieval_runs=retrieval_runs,
            retrieved_chunks_by_run_id=retrieved_chunks_by_run_id,
            provider_usage=provider_usage,
        )

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


def _encode_chat_session_cursor(
    *,
    created_at: datetime,
    session_id: UUID,
) -> str:
    payload = {
        "created_at": created_at.isoformat(),
        "session_id": str(session_id),
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_chat_session_cursor(cursor: str | None) -> tuple[datetime, UUID] | None:
    if cursor is None:
        return None
    try:
        padded_cursor = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded_cursor.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
        created_at = datetime.fromisoformat(payload["created_at"])
        session_id = UUID(payload["session_id"])
    except (
        binascii.Error,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError("invalid chat session cursor") from exc
    return created_at, session_id


def _normalize_session_title(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("session title must not be empty")
    return normalized[:SESSION_TITLE_MAX_LENGTH]


def _derived_session_title(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return value[:SESSION_TITLE_MAX_LENGTH]
