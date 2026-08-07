"""Servicio compartido de chat/tool calling."""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from inspect import signature
from time import monotonic
from typing import Any, Protocol
from uuid import UUID

from adaptive_rag.chat.audit import ChatAuditWriter, NullChatAuditWriter, elapsed_ms
from adaptive_rag.chat.condenser import DeterministicQueryCondenser, QueryCondenser
from adaptive_rag.chat.errors import ChatServiceError, classify_chat_error
from adaptive_rag.chat.history import (
    DEFAULT_HISTORY_LOAD_LIMIT,
    PreparedChatHistory,
    prepare_chat_history,
)
from adaptive_rag.chat.models import (
    DEFAULT_CHAT_HISTORY_MESSAGES,
    ChatHistoryTurn,
    ChatRequest,
    ChatResponse,
    ChatRunnerOutput,
    ChatRunnerRequest,
    ChatToolCall,
)
from adaptive_rag.chat.streaming import (
    ChatStep,
    ChatStepUsage,
    ChatStreamEvent,
    chat_stream_answer_delta_event,
    chat_stream_error_event,
    chat_stream_final_event,
    chat_stream_heartbeat_event,
    chat_stream_session_started_event,
    chat_stream_step_event,
    chat_stream_tool_call_event,
    serialize_chat_step,
)

# Heartbeat interval while the runner is blocked on LLM/retrieval work.
_STREAM_HEARTBEAT_SECONDS = 5.0
from adaptive_rag.chat.tools import (
    ChatKnowledgeProposalTool,
    ChatRetrievalTool,
    ChatTools,
    KnowledgeProposalSubmitter,
    RetrievalSearcher,
)
from adaptive_rag.db.models import CHAT_RETRIEVAL_MAX_LIMIT
from adaptive_rag.provider_usage import ProviderCallRecord
from adaptive_rag.retrieval.payloads import RetrievalResultPayload

logger = logging.getLogger(__name__)

# Bound single-turn user messages to limit request size and prompt cost.
# 32k chars is well below typical context windows yet blocks accidental/abusive dumps.
MAX_CHAT_MESSAGE_CHARS = 32_000


class ChatRunner(Protocol):
    """Runner conversacional inyectable para aislar frameworks agentic."""

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        """Ejecuta una vuelta de chat con tools disponibles."""


class GraphReadinessChecker(Protocol):
    """Reports whether graph retrieval is ready for a project."""

    def __call__(self, project_id: UUID) -> bool:
        """Return True when graph strategy may be selected for the project."""


def _graph_never_ready(_project_id: UUID) -> bool:
    return False


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
        knowledge_proposal_submitter: KnowledgeProposalSubmitter | None = None,
        query_condenser: QueryCondenser | None = None,
        history_message_limit: int = DEFAULT_CHAT_HISTORY_MESSAGES,
        history_load_limit: int = DEFAULT_HISTORY_LOAD_LIMIT,
        graph_readiness: GraphReadinessChecker | None = None,
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
        self._knowledge_proposal_submitter = knowledge_proposal_submitter
        self._query_condenser = (
            query_condenser
            if query_condenser is not None
            else DeterministicQueryCondenser()
        )
        # Verbatim window kept in the prompt; older turns are summarized.
        self._history_message_limit = history_message_limit
        self._history_load_limit = max(history_load_limit, history_message_limit)
        self._graph_readiness = graph_readiness or _graph_never_ready

    def respond(self, request: ChatRequest) -> ChatResponse:
        message = _validate_request(request)

        try:
            session_id = self._audit_writer.start_session(
                request,
                message,
                model_config_json=_runner_model_config(self._runner),
                prompt_version=_runner_prompt_version(self._runner),
            )
        except ValueError as exc:
            raise _session_start_error(exc) from exc
        provider_usage_recorded = False
        prepared = self._prepare_history(request.project_id, session_id)
        history = prepared.turns
        retrieval_query = self._query_condenser.condense(
            history=history,
            message=message,
        )
        runner_request = ChatRunnerRequest(
            project_id=request.project_id,
            message=message,
            user_id=request.user_id,
            retrieval_limit=request.retrieval_limit,
            metadata_filter=request.metadata_filter,
            history=history,
            retrieval_query=retrieval_query,
            user_memory=request.user_memory,
        )
        retrieval_tool = ChatRetrievalTool(
            retrieval_service=self._retrieval_service,
            project_id=request.project_id,
            default_limit=request.retrieval_limit,
            rerank_enabled=request.rerank_enabled,
            rerank_candidate_limit=request.rerank_candidate_limit,
            default_metadata_filter=request.metadata_filter,
            audit_writer=self._audit_writer,
            audit_session_id=session_id,
            graph_ready=self._graph_readiness(request.project_id),
        )
        try:
            user_message_id = None
            if session_id is not None:
                user_message_id = self._audit_writer.record_message(
                    request.project_id,
                    session_id,
                    "user",
                    message,
                )
            knowledge_tool = self._build_knowledge_tool(
                request=request,
                session_id=session_id,
                origin_message_id=user_message_id,
            )
            output = self._runner.run(
                runner_request,
                ChatTools(retrieval=retrieval_tool, knowledge=knowledge_tool),
            )
            citations = _resolve_citations(
                cited_chunk_ids=output.cited_chunk_ids,
                retrieved_results=retrieval_tool.retrieved_results,
            )
            response = ChatResponse(
                answer=_sanitize_chat_answer(
                    output.answer,
                    max_doc=len(citations),
                    source_texts=_source_texts_for_filter(
                        citations,
                        retrieval_tool.retrieved_results,
                    ),
                ),
                citations=citations,
                tool_calls=_collect_tool_calls(retrieval_tool, knowledge_tool),
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
            error = classify_chat_error(exc)
            if session_id is not None:
                provider_usage_recorded = self._record_provider_usage_once(
                    project_id=request.project_id,
                    session_id=session_id,
                    already_recorded=provider_usage_recorded,
                )
                self._audit_writer.fail_session(
                    request.project_id,
                    session_id,
                    error.message,
                )
            if isinstance(exc, ChatServiceError):
                raise
            # Surface provider/runtime failures as ChatServiceError so the API
            # returns a stable 422 (with Retry UX) instead of an opaque 500.
            raise ChatServiceError(
                error.message,
                code=error.code,
                retryable=error.retryable,
            ) from exc

    def stream(self, request: ChatRequest) -> Iterator[ChatStreamEvent]:
        message = _validate_request(request)
        try:
            session_id = self._audit_writer.start_session(
                request,
                message,
                model_config_json=_runner_model_config(self._runner),
                prompt_version=_runner_prompt_version(self._runner),
            )
        except ValueError as exc:
            raise _session_start_error(exc) from exc
        prepared = self._prepare_history(request.project_id, session_id)
        history = prepared.turns
        retrieval_query = self._query_condenser.condense(
            history=history,
            message=message,
        )
        runner_request = ChatRunnerRequest(
            project_id=request.project_id,
            message=message,
            user_id=request.user_id,
            retrieval_limit=request.retrieval_limit,
            metadata_filter=request.metadata_filter,
            history=history,
            retrieval_query=retrieval_query,
            user_memory=request.user_memory,
        )
        retrieval_tool = ChatRetrievalTool(
            retrieval_service=self._retrieval_service,
            project_id=request.project_id,
            default_limit=request.retrieval_limit,
            rerank_enabled=request.rerank_enabled,
            rerank_candidate_limit=request.rerank_candidate_limit,
            default_metadata_filter=request.metadata_filter,
            audit_writer=self._audit_writer,
            audit_session_id=session_id,
            graph_ready=self._graph_readiness(request.project_id),
        )
        return self._stream_response(
            request=request,
            message=message,
            session_id=session_id,
            runner_request=runner_request,
            retrieval_tool=retrieval_tool,
            prepared_history=prepared,
        )

    def _stream_response(
        self,
        *,
        request: ChatRequest,
        message: str,
        session_id: UUID | None,
        runner_request: ChatRunnerRequest,
        retrieval_tool: ChatRetrievalTool,
        prepared_history: PreparedChatHistory | None = None,
    ) -> Iterator[ChatStreamEvent]:
        provider_usage_recorded = False
        answer_start: float | None = None
        retrieval_steps_flushed = False
        try:
            # Record user turn before advertising session_started so an eager
            # commit after that event already has a durable user message.
            user_message_id = None
            if session_id is not None:
                user_message_id = self._audit_writer.record_message(
                    request.project_id,
                    session_id,
                    "user",
                    message,
                )
                yield chat_stream_session_started_event(session_id)
            knowledge_tool = self._build_knowledge_tool(
                request=request,
                session_id=session_id,
                origin_message_id=user_message_id,
            )
            answer_start = monotonic()
            if prepared_history is not None and prepared_history.total_messages > 0:
                yield chat_stream_step_event(
                    ChatStep(
                        id="context",
                        status="done",
                        detail=prepared_history.as_step_detail(),
                    )
                )
            yield chat_stream_step_event(ChatStep(id="answer", status="start"))
            streamed_answer_parts: list[str] = []
            live_steps_emitted = [0]
            output = yield from self._run_runner_with_heartbeats(
                runner_request=runner_request,
                retrieval_tool=retrieval_tool,
                knowledge_tool=knowledge_tool,
                answer_start=answer_start,
                streamed_answer_parts=streamed_answer_parts,
                live_steps_emitted=live_steps_emitted,
            )
            citations = _resolve_citations(
                cited_chunk_ids=output.cited_chunk_ids,
                retrieved_results=retrieval_tool.retrieved_results,
            )
            response = ChatResponse(
                answer=_sanitize_chat_answer(
                    output.answer,
                    max_doc=len(citations),
                    source_texts=_source_texts_for_filter(
                        citations,
                        retrieval_tool.retrieved_results,
                    ),
                ),
                citations=citations,
                tool_calls=_collect_tool_calls(retrieval_tool, knowledge_tool),
                session_id=session_id,
            )
            provider_usage_records = self._read_provider_usage_records()
            answer_step = ChatStep(
                id="answer",
                status="done",
                elapsed_ms=elapsed_ms(answer_start),
                detail={"sources": len(response.citations)},
                usage=_chat_step_usage(provider_usage_records),
            )
            # Emit any retrieval steps not already streamed live mid-tool.
            for step in retrieval_tool.steps[live_steps_emitted[0] :]:
                yield chat_stream_step_event(step)
            retrieval_steps_flushed = True
            yield chat_stream_step_event(answer_step)
            for tool_call in response.tool_calls:
                yield chat_stream_tool_call_event(tool_call)
            streamed = "".join(streamed_answer_parts)
            if response.answer:
                if not streamed:
                    yield chat_stream_answer_delta_event(response.answer)
                elif response.answer.startswith(streamed):
                    rest = response.answer[len(streamed) :]
                    if rest:
                        yield chat_stream_answer_delta_event(rest)
            if session_id is not None:
                context_steps: list[ChatStep] = []
                if (
                    prepared_history is not None
                    and prepared_history.total_messages > 0
                ):
                    context_steps.append(
                        ChatStep(
                            id="context",
                            status="done",
                            detail=prepared_history.as_step_detail(),
                        )
                    )
                self._audit_writer.record_message(
                    request.project_id,
                    session_id,
                    "assistant",
                    response.answer,
                    metadata_json={
                        "steps": [
                            serialize_chat_step(step)
                            for step in (
                                *context_steps,
                                *retrieval_tool.steps,
                                answer_step,
                            )
                            if step.status != "start"
                        ]
                    },
                )
                provider_usage_recorded = self._record_provider_usage_records_once(
                    project_id=request.project_id,
                    session_id=session_id,
                    already_recorded=provider_usage_recorded,
                    records=provider_usage_records,
                )
                self._audit_writer.succeed_session(request.project_id, session_id)
            yield chat_stream_final_event(response)
        except GeneratorExit:
            if session_id is not None:
                provider_usage_recorded = self._record_provider_usage_once(
                    project_id=request.project_id,
                    session_id=session_id,
                    already_recorded=provider_usage_recorded,
                )
                try:
                    self._audit_writer.cancel_session(
                        request.project_id,
                        session_id,
                        "client_disconnected",
                    )
                except Exception as audit_exc:
                    logger.warning(
                        "chat_cancel_audit_failed",
                        extra={"error_type": type(audit_exc).__name__},
                        exc_info=audit_exc,
                    )
            raise
        except Exception as exc:
            if not retrieval_steps_flushed:
                for step in retrieval_tool.steps:
                    yield chat_stream_step_event(step)
            error = classify_chat_error(exc)
            yield chat_stream_step_event(
                ChatStep(
                    id="answer",
                    status="error",
                    elapsed_ms=(
                        elapsed_ms(answer_start) if answer_start is not None else None
                    ),
                    detail={
                        "error": error.message,
                        "code": error.code,
                        "retryable": error.retryable,
                    },
                )
            )
            if session_id is not None:
                provider_usage_recorded = self._record_provider_usage_once(
                    project_id=request.project_id,
                    session_id=session_id,
                    already_recorded=provider_usage_recorded,
                )
                self._audit_writer.fail_session(
                    request.project_id,
                    session_id,
                    error.message,
                )
            yield chat_stream_error_event(
                error.message,
                code=error.code,
                retryable=error.retryable,
            )

    def _run_runner_with_heartbeats(
        self,
        *,
        runner_request: ChatRunnerRequest,
        retrieval_tool: ChatRetrievalTool,
        knowledge_tool: ChatKnowledgeProposalTool | None,
        answer_start: float,
        streamed_answer_parts: list[str],
        live_steps_emitted: list[int],
    ) -> Iterator[ChatStreamEvent]:
        """Run the chat runner off the stream loop; emit heartbeats + deltas.

        Yields retrieval step / heartbeat / answer_delta events while work is
        in flight, then returns the ``ChatRunnerOutput`` (``yield from``
        captures the return).
        """

        tools = ChatTools(retrieval=retrieval_tool, knowledge=knowledge_tool)
        holder: dict[str, Any] = {}
        delta_queue: queue.Queue[str | None] = queue.Queue()
        step_queue: queue.Queue[ChatStep] = queue.Queue()
        cancel_event = threading.Event()
        client = getattr(self._runner, "client", None)
        if client is not None and hasattr(client, "set_cancel_event"):
            client.set_cancel_event(cancel_event)

        def _on_answer_delta(text: str) -> None:
            if text:
                delta_queue.put(text)

        def _on_step(step: ChatStep) -> None:
            step_queue.put(step)

        retrieval_tool.set_on_step(_on_step)

        def _run() -> None:
            try:
                run_kwargs: dict[str, Any] = {}
                try:
                    parameters = signature(self._runner.run).parameters
                except (TypeError, ValueError):
                    parameters = {}
                if "on_answer_delta" in parameters:
                    run_kwargs["on_answer_delta"] = _on_answer_delta
                holder["output"] = self._runner.run(
                    runner_request, tools, **run_kwargs
                )
            except Exception as exc:  # noqa: BLE001 — re-raised on main thread
                holder["error"] = exc
            finally:
                delta_queue.put(None)

        def _drain_steps() -> Iterator[ChatStreamEvent]:
            while True:
                try:
                    step = step_queue.get_nowait()
                except queue.Empty:
                    break
                live_steps_emitted[0] += 1
                yield chat_stream_step_event(step)

        # Exclusive DB access: main thread only yields stream events (no session
        # I/O) while the worker runs the runner/tools; after the future completes
        # the main thread resumes audit I/O.
        # Do not block forever on cancel: shutdown(wait=False) so disconnect
        # can fail_session quickly while the worker aborts httpx best-effort.
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_run)
        last_heartbeat = monotonic()
        cancelled = False
        try:
            while not future.done():
                if cancel_event.is_set():
                    cancelled = True
                    break
                yield from _drain_steps()
                try:
                    item = delta_queue.get(timeout=0.1)
                except queue.Empty:
                    item = object()
                if item is None:
                    break
                if isinstance(item, str):
                    streamed_answer_parts.append(item)
                    yield chat_stream_answer_delta_event(item)
                now = monotonic()
                if now - last_heartbeat >= _STREAM_HEARTBEAT_SECONDS:
                    yield chat_stream_heartbeat_event(
                        elapsed_ms=elapsed_ms(answer_start)
                    )
                    last_heartbeat = now
            # Drain remaining steps/deltas after worker finishes (unless cancelled).
            if not cancelled:
                yield from _drain_steps()
                while True:
                    try:
                        item = delta_queue.get_nowait()
                    except queue.Empty:
                        break
                    if item is None:
                        break
                    if isinstance(item, str):
                        streamed_answer_parts.append(item)
                        yield chat_stream_answer_delta_event(item)
                yield from _drain_steps()
        except GeneratorExit:
            cancelled = True
            cancel_event.set()
            if client is not None and hasattr(client, "request_cancel"):
                client.request_cancel()
            delta_queue.put(None)
            executor.shutdown(wait=False, cancel_futures=True)
            raise
        finally:
            retrieval_tool.set_on_step(None)
            if not cancelled:
                executor.shutdown(wait=True, cancel_futures=False)
            else:
                executor.shutdown(wait=False, cancel_futures=True)

        if cancelled:
            raise ChatServiceError(
                "client_disconnected",
                code="client_disconnected",
                retryable=False,
            )
        if "error" in holder:
            raise holder["error"]
        try:
            future.result(timeout=0.1)
        except Exception:
            pass
        output = holder.get("output")
        if not isinstance(output, ChatRunnerOutput):
            raise ChatServiceError("chat runner returned no output")
        return output

    def _prepare_history(
        self,
        project_id: UUID,
        session_id: UUID | None,
    ) -> PreparedChatHistory:
        if session_id is None:
            return PreparedChatHistory(
                turns=(),
                summary=None,
                total_messages=0,
                kept_recent=0,
                summarized_messages=0,
            )
        raw_turns = self._audit_writer.list_history_turns(
            project_id=project_id,
            session_id=session_id,
            limit=self._history_load_limit,
        )
        return prepare_chat_history(
            raw_turns,
            keep_recent=self._history_message_limit,
        )

    def _load_history(
        self,
        project_id: UUID,
        session_id: UUID | None,
    ) -> tuple[ChatHistoryTurn, ...]:
        return self._prepare_history(project_id, session_id).turns

    def _build_knowledge_tool(
        self,
        *,
        request: ChatRequest,
        session_id: UUID | None,
        origin_message_id: UUID | None,
    ) -> ChatKnowledgeProposalTool | None:
        if self._knowledge_proposal_submitter is None:
            return None
        # Anonymous / bootstrap turns cannot persist proposals; omit tools so a
        # failed commit does not abort the whole chat turn.
        if request.user_id is None:
            return None
        return ChatKnowledgeProposalTool(
            submitter=self._knowledge_proposal_submitter,
            project_id=request.project_id,
            submitted_by_user_id=request.user_id,
            origin_session_id=session_id,
            origin_message_id=origin_message_id,
            audit_writer=self._audit_writer,
        )

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
                exc_info=exc,
            )
        return True

    def _read_provider_usage_records(self) -> tuple[ProviderCallRecord, ...]:
        try:
            return self._provider_usage_records()
        except Exception as exc:
            logger.warning(
                "chat_provider_usage_audit_failed",
                extra={"error_type": type(exc).__name__},
                exc_info=exc,
            )
            return ()

    def _record_provider_usage_records_once(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
        already_recorded: bool,
        records: tuple[ProviderCallRecord, ...],
    ) -> bool:
        if already_recorded:
            return True
        try:
            self._audit_writer.record_provider_usage(project_id, session_id, records)
        except Exception as exc:
            logger.warning(
                "chat_provider_usage_audit_failed",
                extra={"error_type": type(exc).__name__},
                exc_info=exc,
            )
        return True


def _empty_provider_usage_records() -> tuple[ProviderCallRecord, ...]:
    return ()


def _session_start_error(exc: BaseException) -> ChatServiceError:
    message_text = str(exc)
    if message_text == "session is archived":
        return ChatServiceError(
            "This chat session is archived. Start a new session to continue.",
            code="session_archived",
            retryable=False,
        )
    if message_text == "chat session not found":
        return ChatServiceError(
            message_text,
            code="session_not_found",
            retryable=False,
        )
    return ChatServiceError(message_text)


def _collect_tool_calls(
    retrieval_tool: ChatRetrievalTool,
    knowledge_tool: ChatKnowledgeProposalTool | None,
) -> tuple[ChatToolCall, ...]:
    calls = list(retrieval_tool.tool_calls)
    if knowledge_tool is not None:
        calls.extend(knowledge_tool.tool_calls)
    return tuple(calls)


def _chat_step_usage(
    records: tuple[ProviderCallRecord, ...],
) -> ChatStepUsage | None:
    chat_record = next(
        (record for record in records if record.operation == "chat"),
        None,
    )
    if chat_record is None:
        return None
    return ChatStepUsage(
        slot="chat",
        provider=chat_record.provider,
        model=chat_record.model,
        input_tokens=chat_record.usage.input_tokens,
        output_tokens=chat_record.usage.output_tokens,
        total_tokens=chat_record.usage.total_tokens,
        estimated_cost_usd=chat_record.estimated_cost_usd,
        cost_source=chat_record.usage_source,
    )


def _runner_model_config(runner: ChatRunner) -> dict[str, str] | None:
    provider = _string_attr(runner, "provider_name")
    model = _string_attr(runner, "model_name")
    if provider is None or model is None:
        return None
    config: dict[str, str] = {"provider": provider, "model": model}
    fallback = _string_attr(runner, "fallback_model_name")
    if fallback is not None:
        config["fallback_model"] = fallback
    used = _string_attr(runner, "last_used_model")
    if used is not None:
        config["resolved_model"] = used
    if bool(getattr(runner, "used_fallback", False)):
        config["used_fallback"] = "true"
    return config


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
    if request.retrieval_limit > CHAT_RETRIEVAL_MAX_LIMIT:
        raise ChatServiceError(
            f"retrieval_limit must be between 1 and {CHAT_RETRIEVAL_MAX_LIMIT}"
        )
    if request.rerank_candidate_limit <= 0:
        raise ChatServiceError("rerank_candidate_limit must be positive")
    if request.rerank_candidate_limit > CHAT_RETRIEVAL_MAX_LIMIT:
        raise ChatServiceError(
            f"rerank_candidate_limit must be between 1 and {CHAT_RETRIEVAL_MAX_LIMIT}"
        )
    if (
        request.rerank_enabled
        and request.rerank_candidate_limit < request.retrieval_limit
    ):
        raise ChatServiceError(
            "rerank_candidate_limit must be greater than or equal to retrieval_limit"
        )
    return message


def _validate_message(message: str) -> str:
    if len(message) > MAX_CHAT_MESSAGE_CHARS:
        raise ChatServiceError(
            f"message must be at most {MAX_CHAT_MESSAGE_CHARS} characters"
        )
    value = message.strip()
    if not value:
        raise ChatServiceError("message must not be empty")
    return value


def _resolve_citations(
    *,
    cited_chunk_ids: tuple[UUID, ...],
    retrieved_results: dict[UUID, RetrievalResultPayload],
) -> tuple[RetrievalResultPayload, ...]:
    """Map model-cited chunk ids to retrieval payloads.

    Unknown ids are skipped (not fatal): production models occasionally emit a
    stale/hallucinated UUID while still producing a usable answer grounded in
    valid citations. Fabricated ids never invent retrieval content.
    """

    citations: list[RetrievalResultPayload] = []
    seen: set[UUID] = set()
    for chunk_id in cited_chunk_ids:
        if chunk_id in seen:
            continue
        payload = retrieved_results.get(chunk_id)
        if payload is None:
            logger.warning(
                "chat_citation_skipped_unknown",
                extra={"chunk_id": str(chunk_id)},
            )
            continue
        seen.add(chunk_id)
        citations.append(payload)
    return tuple(citations)


def _redact_chat_answer(answer: str) -> str:
    from adaptive_rag.security.secrets import redact_secrets

    redacted, _count = redact_secrets(answer)
    return redacted


def _source_texts_for_filter(
    citations: tuple[RetrievalResultPayload, ...],
    retrieved_results: dict[UUID, RetrievalResultPayload],
) -> list[str]:
    """Collect unique retrieved/cited snippets for regurgitation filtering."""

    texts: list[str] = []
    seen: set[str] = set()
    for payload in (*citations, *retrieved_results.values()):
        snippet = payload["citation"]["snippet"]
        if not snippet or snippet in seen:
            continue
        seen.add(snippet)
        texts.append(snippet)
    return texts


def _sanitize_chat_answer(
    answer: str,
    *,
    max_doc: int,
    source_texts: Sequence[str] = (),
) -> str:
    """Secret redaction + citation markers + source regurgitation scrub."""

    from adaptive_rag.security.citation_markers import filter_citation_markers
    from adaptive_rag.security.secrets import redact_secrets
    from adaptive_rag.security.source_regurgitation import filter_source_regurgitation

    redacted, _count = redact_secrets(answer)
    filtered, _fabricated = filter_citation_markers(redacted, max_doc=max_doc)
    cleaned, _regurg = filter_source_regurgitation(filtered, source_texts)
    return cleaned
