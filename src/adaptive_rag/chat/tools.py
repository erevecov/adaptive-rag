"""Tools disponibles para runners conversacionales."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any, Protocol
from uuid import UUID, uuid4

from adaptive_rag.chat.audit import (
    ChatAuditWriter,
    NullChatAuditWriter,
    elapsed_ms,
)
from adaptive_rag.chat.errors import ChatServiceError
from adaptive_rag.chat.models import ChatToolCall
from adaptive_rag.chat.streaming import ChatStep
from adaptive_rag.retrieval import (
    RetrievalMetadataFilter,
    RetrievalRerankOptions,
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


class KnowledgeProposalSubmitter(Protocol):
    """Backend que prepara un draft de conocimiento desde chat."""

    def commit(
        self,
        *,
        project_id: UUID,
        submitted_by_user_id: UUID,
        knowledge_text: str,
        scope: str,
        origin_session_id: UUID | None,
        origin_message_id: UUID | None,
        draft_id: str | None = None,
    ) -> KnowledgeProposalSubmissionResult:
        """Crea un draft revisable y devuelve un resumen serializable."""


@dataclass(frozen=True, slots=True)
class KnowledgeProposalSubmissionResult:
    """Resultado minimo de un draft creado desde la tool de chat."""

    draft_id: str
    status: str
    proposed_text: str
    review_action: str
    scope: str
    approved_source_id: UUID | None = None

    def as_summary(self) -> dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "proposed_text": self.proposed_text,
            "review_action": self.review_action,
            "scope": self.scope,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class ChatRetrievalToolResult:
    """Resultado serializable de la tool de retrieval."""

    results: tuple[RetrievalResultPayload, ...]


@dataclass(frozen=True, slots=True)
class ChatTools:
    """Contenedor de tools entregadas al runner conversacional."""

    retrieval: ChatRetrievalTool
    knowledge: ChatKnowledgeProposalTool | None = None


class ChatRetrievalTool:
    """Tool que delega retrieval al servicio M4."""

    name = "retrieval.search"

    def __init__(
        self,
        *,
        retrieval_service: RetrievalSearcher,
        project_id: UUID,
        default_limit: int,
        rerank_enabled: bool = False,
        rerank_candidate_limit: int | None = None,
        default_metadata_filter: RetrievalMetadataFilter | None,
        audit_writer: ChatAuditWriter | None = None,
        audit_session_id: UUID | None = None,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._project_id = project_id
        self._default_limit = default_limit
        self._rerank_enabled = rerank_enabled
        self._rerank_candidate_limit = rerank_candidate_limit
        self._default_metadata_filter = default_metadata_filter
        self._audit_writer = (
            audit_writer if audit_writer is not None else NullChatAuditWriter()
        )
        self._audit_session_id = audit_session_id
        self._tool_calls: list[ChatToolCall] = []
        self._retrieved_results: dict[UUID, RetrievalResultPayload] = {}
        self._steps: list[ChatStep] = []

    @property
    def tool_calls(self) -> tuple[ChatToolCall, ...]:
        return tuple(self._tool_calls)

    @property
    def retrieved_results(self) -> dict[UUID, RetrievalResultPayload]:
        return dict(self._retrieved_results)

    @property
    def steps(self) -> tuple[ChatStep, ...]:
        return tuple(self._steps)

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
        self._record_step(
            ChatStep(
                id="retrieval",
                status="start",
                detail={
                    "query": query,
                    "limit": active_limit,
                    "strategy": "dense_sparse",
                },
            )
        )
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
                    rerank=self._rerank_options(),
                    strategy="dense_sparse",
                )
            )
        except RetrievalServiceError as exc:
            latency_ms = elapsed_ms(start)
            self._record_step(
                ChatStep(
                    id="retrieval",
                    status="error",
                    elapsed_ms=latency_ms,
                    detail={
                        "query": query,
                        "limit": active_limit,
                        "error": str(exc),
                    },
                )
            )
            if self._audit_session_id is not None:
                self._audit_writer.fail_retrieval_tool(
                    self._project_id,
                    self._audit_session_id,
                    audit_tool_call_id,
                    str(exc),
                    latency_ms,
                )
            raise ChatServiceError(str(exc)) from exc
        except Exception as exc:
            latency_ms = elapsed_ms(start)
            self._record_step(
                ChatStep(
                    id="retrieval",
                    status="error",
                    elapsed_ms=latency_ms,
                    detail={
                        "query": query,
                        "limit": active_limit,
                        "error": str(exc),
                    },
                )
            )
            if self._audit_session_id is not None:
                self._audit_writer.fail_retrieval_tool(
                    self._project_id,
                    self._audit_session_id,
                    audit_tool_call_id,
                    str(exc),
                    latency_ms,
                )
            raise

        latency_ms = elapsed_ms(start)
        payloads = tuple(serialize_retrieval_results(results))
        strategy = _strategy_for_results(results)
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
        self._record_step(
            ChatStep(
                id="retrieval",
                status="done",
                elapsed_ms=latency_ms,
                detail={
                    "query": query,
                    "limit": active_limit,
                    "result_count": len(payloads),
                    "strategy": strategy,
                },
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
                strategy,
            )
        return ChatRetrievalToolResult(results=payloads)

    def _rerank_options(self) -> RetrievalRerankOptions | None:
        if not self._rerank_enabled:
            return None
        if self._rerank_candidate_limit is None:
            raise ChatServiceError(
                "rerank_candidate_limit is required when rerank is enabled"
            )
        return RetrievalRerankOptions(candidate_limit=self._rerank_candidate_limit)

    def _record_step(self, step: ChatStep) -> None:
        self._steps.append(step)


class ChatKnowledgeProposalTool:
    """Tool que crea drafts de conocimiento desde el turno de chat."""

    name = "commit_knowledge"
    approve_name = "approve_knowledge"
    cancel_name = "cancel_knowledge"
    refine_name = "refine_knowledge"

    def __init__(
        self,
        *,
        submitter: KnowledgeProposalSubmitter,
        project_id: UUID,
        submitted_by_user_id: UUID | None,
        origin_session_id: UUID | None,
        origin_message_id: UUID | None,
        audit_writer: ChatAuditWriter | None = None,
    ) -> None:
        self._submitter = submitter
        self._project_id = project_id
        self._submitted_by_user_id = submitted_by_user_id
        self._origin_session_id = origin_session_id
        self._origin_message_id = origin_message_id
        self._audit_writer = (
            audit_writer if audit_writer is not None else NullChatAuditWriter()
        )
        self._tool_calls: list[ChatToolCall] = []

    @property
    def tool_calls(self) -> tuple[ChatToolCall, ...]:
        return tuple(self._tool_calls)

    def commit(
        self,
        *,
        knowledge_text: str,
        scope: str = "message",
        draft_id: str | None = None,
    ) -> dict[str, Any]:
        text = knowledge_text.strip()
        if not text:
            raise ChatServiceError("knowledge_text must not be empty")
        normalized_scope = _normalize_knowledge_scope(scope)
        if self._submitted_by_user_id is None:
            raise ChatServiceError("authenticated user required to commit knowledge")
        submitted_by_user_id = self._submitted_by_user_id

        normalized_draft_id = draft_id.strip() if draft_id is not None else None
        if normalized_draft_id == "":
            raise ChatServiceError("draft_id must not be empty")
        arguments = {
            "knowledge_text": text,
            "scope": normalized_scope,
        }
        if normalized_draft_id is not None:
            arguments["draft_id"] = normalized_draft_id

        def action() -> dict[str, Any]:
            result = self._submitter.commit(
                project_id=self._project_id,
                submitted_by_user_id=submitted_by_user_id,
                knowledge_text=text,
                scope=normalized_scope,
                origin_session_id=self._origin_session_id,
                origin_message_id=self._origin_message_id,
                draft_id=normalized_draft_id,
            )
            return result.as_summary()

        return self._record_lifecycle_tool(
            tool_name=self.name,
            arguments=arguments,
            action=action,
        )

    def refine(
        self,
        *,
        draft_id: str,
        knowledge_text: str,
        scope: str = "message",
    ) -> dict[str, Any]:
        normalized_draft_id = draft_id.strip()
        if not normalized_draft_id:
            raise ChatServiceError("draft_id must not be empty")
        text = knowledge_text.strip()
        if not text:
            raise ChatServiceError("knowledge_text must not be empty")
        normalized_scope = _normalize_knowledge_scope(scope)
        if self._submitted_by_user_id is None:
            raise ChatServiceError("authenticated user required to refine knowledge")
        submitted_by_user_id = self._submitted_by_user_id

        arguments = {
            "draft_id": normalized_draft_id,
            "knowledge_text": text,
            "scope": normalized_scope,
        }

        def action() -> dict[str, Any]:
            result = self._submitter.commit(
                project_id=self._project_id,
                submitted_by_user_id=submitted_by_user_id,
                knowledge_text=text,
                scope=normalized_scope,
                origin_session_id=self._origin_session_id,
                origin_message_id=self._origin_message_id,
                draft_id=normalized_draft_id,
            )
            summary = result.as_summary()
            summary["knowledge_lifecycle"] = {
                "action": "refine",
                "draft_id": normalized_draft_id,
            }
            return summary

        return self._record_lifecycle_tool(
            tool_name=self.refine_name,
            arguments=arguments,
            action=action,
        )

    def cancel(self, *, draft_id: str | None = None) -> dict[str, Any]:
        normalized_draft_id = draft_id.strip() if draft_id is not None else None
        if normalized_draft_id == "":
            raise ChatServiceError("draft_id must not be empty")
        arguments: dict[str, Any] = {}
        if normalized_draft_id is not None:
            arguments["draft_id"] = normalized_draft_id

        def action() -> dict[str, Any]:
            summary: dict[str, Any] = {
                "status": "cancelled",
                "knowledge_lifecycle": {
                    "action": "cancel",
                },
            }
            if normalized_draft_id is not None:
                summary["draft_id"] = normalized_draft_id
                summary["knowledge_lifecycle"]["draft_id"] = normalized_draft_id
            else:
                summary["knowledge_lifecycle"]["all_pending"] = True
            return summary

        return self._record_lifecycle_tool(
            tool_name=self.cancel_name,
            arguments=arguments,
            action=action,
        )

    def approve(self, *, draft_id: str) -> dict[str, Any]:
        normalized_draft_id = draft_id.strip()
        if not normalized_draft_id:
            raise ChatServiceError("draft_id must not be empty")
        arguments = {"draft_id": normalized_draft_id}

        def action() -> dict[str, Any]:
            return {
                "draft_id": normalized_draft_id,
                "status": "approval_requested",
                "knowledge_lifecycle": {
                    "action": "approve",
                    "draft_id": normalized_draft_id,
                },
            }

        return self._record_lifecycle_tool(
            tool_name=self.approve_name,
            arguments=arguments,
            action=action,
        )

    def _record_lifecycle_tool(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        action: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        start = monotonic()
        audit_tool_call_id = self._audit_writer.start_tool_call(
            self._project_id,
            self._origin_session_id,
            tool_name,
            arguments,
        )
        try:
            summary = action()
        except ValueError as exc:
            self._audit_writer.fail_tool_call(
                self._project_id,
                self._origin_session_id,
                audit_tool_call_id,
                str(exc),
                elapsed_ms(start),
            )
            raise ChatServiceError(str(exc)) from exc
        except Exception as exc:
            self._audit_writer.fail_tool_call(
                self._project_id,
                self._origin_session_id,
                audit_tool_call_id,
                str(exc),
                elapsed_ms(start),
            )
            raise

        self._audit_writer.complete_tool_call(
            self._project_id,
            self._origin_session_id,
            audit_tool_call_id,
            summary,
            elapsed_ms(start),
        )
        self._tool_calls.append(
            ChatToolCall(
                name=tool_name,
                arguments=arguments,
                result_summary=summary,
            )
        )
        return summary


def new_knowledge_draft_id() -> str:
    """Return a stable user-visible id for a chat knowledge draft."""

    return f"draft-{uuid4()}"


def _normalize_knowledge_scope(scope: str) -> str:
    normalized = scope.strip().lower()
    if normalized not in {"message", "session"}:
        raise ChatServiceError("knowledge scope must be message or session")
    return normalized


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
