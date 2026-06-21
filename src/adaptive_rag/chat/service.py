"""Servicio compartido de chat/tool calling."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from typing import Any, Protocol
from uuid import UUID

from adaptive_rag.chat.audit import ChatAuditWriter, NullChatAuditWriter
from adaptive_rag.chat.errors import ChatServiceError
from adaptive_rag.chat.models import (
    ChatRequest,
    ChatResponse,
    ChatRunnerOutput,
    ChatRunnerRequest,
)
from adaptive_rag.chat.streaming import (
    ChatStreamEvent,
    chat_stream_answer_delta_event,
    chat_stream_error_event,
    chat_stream_final_event,
    chat_stream_session_started_event,
    chat_stream_tool_call_event,
)
from adaptive_rag.chat.tools import ChatRetrievalTool, ChatTools, RetrievalSearcher
from adaptive_rag.provider_usage import ProviderCallRecord
from adaptive_rag.retrieval.payloads import RetrievalResultPayload

logger = logging.getLogger(__name__)


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
        audit_writer: ChatAuditWriter | None = None,
        provider_usage_records: Callable[
            [],
            tuple[ProviderCallRecord, ...],
        ]
        | None = None,
    ) -> None:
        self._runner = runner
        self._retrieval_service = retrieval_service
        self._audit_writer = (
            audit_writer if audit_writer is not None else NullChatAuditWriter()
        )
        self._provider_usage_records = (
            provider_usage_records
            if provider_usage_records is not None
            else _empty_provider_usage_records
        )

    def respond(self, request: ChatRequest) -> ChatResponse:
        message = _validate_request(request)

        session_id = self._audit_writer.start_session(
            request,
            message,
            model_config_json=_runner_model_config(self._runner),
            prompt_version=_runner_prompt_version(self._runner),
        )
        provider_usage_recorded = False
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
            audit_writer=self._audit_writer,
            audit_session_id=session_id,
        )
        try:
            if session_id is not None:
                self._audit_writer.record_message(
                    request.project_id,
                    session_id,
                    "user",
                    message,
                )
            output = self._runner.run(
                runner_request,
                ChatTools(retrieval=retrieval_tool),
            )
            citations = _resolve_citations(
                cited_chunk_ids=output.cited_chunk_ids,
                retrieved_results=retrieval_tool.retrieved_results,
            )
            response = ChatResponse(
                answer=output.answer,
                citations=citations,
                tool_calls=retrieval_tool.tool_calls,
                session_id=session_id,
            )
            if session_id is not None:
                self._audit_writer.record_message(
                    request.project_id,
                    session_id,
                    "assistant",
                    response.answer,
                )
                provider_usage_recorded = self._record_provider_usage_once(
                    project_id=request.project_id,
                    session_id=session_id,
                    already_recorded=provider_usage_recorded,
                )
                self._audit_writer.succeed_session(request.project_id, session_id)
            return response
        except Exception as exc:
            if session_id is not None:
                provider_usage_recorded = self._record_provider_usage_once(
                    project_id=request.project_id,
                    session_id=session_id,
                    already_recorded=provider_usage_recorded,
                )
                self._audit_writer.fail_session(
                    request.project_id,
                    session_id,
                    str(exc),
                )
            raise

    def stream(self, request: ChatRequest) -> Iterator[ChatStreamEvent]:
        message = _validate_request(request)
        session_id = self._audit_writer.start_session(
            request,
            message,
            model_config_json=_runner_model_config(self._runner),
            prompt_version=_runner_prompt_version(self._runner),
        )
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
            audit_writer=self._audit_writer,
            audit_session_id=session_id,
        )
        return self._stream_response(
            request=request,
            message=message,
            session_id=session_id,
            runner_request=runner_request,
            retrieval_tool=retrieval_tool,
        )

    def _stream_response(
        self,
        *,
        request: ChatRequest,
        message: str,
        session_id: UUID | None,
        runner_request: ChatRunnerRequest,
        retrieval_tool: ChatRetrievalTool,
    ) -> Iterator[ChatStreamEvent]:
        provider_usage_recorded = False
        try:
            if session_id is not None:
                yield chat_stream_session_started_event(session_id)
                self._audit_writer.record_message(
                    request.project_id,
                    session_id,
                    "user",
                    message,
                )
            output = self._runner.run(
                runner_request,
                ChatTools(retrieval=retrieval_tool),
            )
            citations = _resolve_citations(
                cited_chunk_ids=output.cited_chunk_ids,
                retrieved_results=retrieval_tool.retrieved_results,
            )
            response = ChatResponse(
                answer=output.answer,
                citations=citations,
                tool_calls=retrieval_tool.tool_calls,
                session_id=session_id,
            )
            for tool_call in response.tool_calls:
                yield chat_stream_tool_call_event(tool_call)
            if response.answer:
                yield chat_stream_answer_delta_event(response.answer)
            if session_id is not None:
                self._audit_writer.record_message(
                    request.project_id,
                    session_id,
                    "assistant",
                    response.answer,
                )
                provider_usage_recorded = self._record_provider_usage_once(
                    project_id=request.project_id,
                    session_id=session_id,
                    already_recorded=provider_usage_recorded,
                )
                self._audit_writer.succeed_session(request.project_id, session_id)
            yield chat_stream_final_event(response)
        except Exception as exc:
            if session_id is not None:
                provider_usage_recorded = self._record_provider_usage_once(
                    project_id=request.project_id,
                    session_id=session_id,
                    already_recorded=provider_usage_recorded,
                )
                self._audit_writer.fail_session(
                    request.project_id,
                    session_id,
                    str(exc),
                )
            yield chat_stream_error_event(str(exc))

    def _record_provider_usage_once(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
        already_recorded: bool,
    ) -> bool:
        if already_recorded:
            return True
        try:
            records = self._provider_usage_records()
            self._audit_writer.record_provider_usage(project_id, session_id, records)
        except Exception as exc:
            logger.warning(
                "chat_provider_usage_audit_failed",
                extra={"error_type": type(exc).__name__},
            )
        return True


def _empty_provider_usage_records() -> tuple[ProviderCallRecord, ...]:
    return ()


def _runner_model_config(runner: ChatRunner) -> dict[str, str] | None:
    provider = _string_attr(runner, "provider_name")
    model = _string_attr(runner, "model_name")
    if provider is None or model is None:
        return None
    return {"provider": provider, "model": model}


def _runner_prompt_version(runner: ChatRunner) -> str | None:
    return _string_attr(runner, "prompt_version")


def _string_attr(value: object, name: str) -> str | None:
    attr: Any = getattr(value, name, None)
    if isinstance(attr, str):
        stripped = attr.strip()
        if stripped:
            return stripped
    return None


def _validate_request(request: ChatRequest) -> str:
    message = _validate_message(request.message)
    if request.retrieval_limit <= 0:
        raise ChatServiceError("retrieval_limit must be positive")
    return message


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
