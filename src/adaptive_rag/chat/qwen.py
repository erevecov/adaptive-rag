"""Runner live de chat Qwen sobre endpoint OpenAI-compatible."""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol
from uuid import UUID

import httpx

from adaptive_rag.chat.models import ChatRunnerOutput, ChatRunnerRequest
from adaptive_rag.chat.tools import ChatRetrievalToolResult, ChatTools
from adaptive_rag.provider_usage import (
    ProviderBudgetExceededError,
    ProviderBudgetGuard,
    ProviderPriceCatalog,
    ProviderUsageTracker,
    build_failure_record,
    build_success_record,
    record_with_budget,
)

ChatMessage = dict[str, Any]
ChatToolDefinition = dict[str, Any]
ChatCompletionResponse = dict[str, Any]

_RETRIEVAL_TOOL_NAME = "retrieval_search"
_KNOWLEDGE_PROPOSAL_TOOL_NAME = "commit_knowledge"
_KNOWLEDGE_APPROVAL_TOOL_NAME = "approve_knowledge"
_KNOWLEDGE_CANCELLATION_TOOL_NAME = "cancel_knowledge"
_KNOWLEDGE_REFINEMENT_TOOL_NAME = "refine_knowledge"


class QwenChatRunnerError(ValueError):
    """Error estable para el runner live de chat Qwen."""


class QwenChatClient(Protocol):
    def create_chat_completion(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        tools: list[ChatToolDefinition] | None = None,
        on_answer_delta: Callable[[str], None] | None = None,
    ) -> ChatCompletionResponse:
        """Ejecuta una llamada chat completion compatible con OpenAI."""

    def request_cancel(self) -> None:
        """Best-effort cancel of the in-flight HTTP call."""


@dataclass(slots=True)
class QwenChatRunner:
    """Implementa ChatRunner usando Qwen con tool calling de retrieval."""

    model_name: str
    client: QwenChatClient
    provider_name: str = "qwen"
    # Optional second model tried once after primary 429/5xx exhaustion.
    fallback_model_name: str | None = None
    last_used_model: str | None = field(default=None, init=False, repr=False)
    used_fallback: bool = field(default=False, init=False, repr=False)

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
        *,
        on_answer_delta: Callable[[str], None] | None = None,
    ) -> ChatRunnerOutput:
        self.used_fallback = False
        try:
            output = self._run_with_model(
                self.model_name,
                request,
                tools,
                on_answer_delta=on_answer_delta,
            )
            self.last_used_model = self.model_name
            return output
        except QwenChatRunnerError as exc:
            if not _should_use_fallback(exc, self.fallback_model_name, self.model_name):
                raise
            output = self._run_with_model(
                self.fallback_model_name or self.model_name,
                request,
                tools,
                on_answer_delta=on_answer_delta,
            )
            self.last_used_model = self.fallback_model_name
            self.used_fallback = True
            return output

    def _run_with_model(
        self,
        model_name: str,
        request: ChatRunnerRequest,
        tools: ChatTools,
        *,
        on_answer_delta: Callable[[str], None] | None = None,
    ) -> ChatRunnerOutput:
        messages = _initial_messages(request)
        first_response = self.client.create_chat_completion(
            model=model_name,
            messages=messages,
            tools=_tool_schemas(tools),
        )
        first_message = _first_message(first_response)
        tool_calls = _tool_calls(first_message)

        if tool_calls:
            messages.append(_assistant_tool_call_message(first_message, tool_calls))
            for tool_call in tool_calls:
                result = _execute_tool_call(
                    tool_call,
                    request=request,
                    tools=tools,
                )
                messages.append(_tool_result_message(tool_call, result))
            final_response = self.client.create_chat_completion(
                model=model_name,
                messages=messages,
                on_answer_delta=on_answer_delta,
            )
            final_message = _first_message(final_response)
            return _parse_runner_output(_message_content(final_message))

        # No tool calls: use the first completion (avoid a second provider call).
        # Emit progressive deltas from the already-complete answer for UI stream.
        output = _parse_runner_output(_message_content(first_message))
        if on_answer_delta is not None and output.answer:
            on_answer_delta(output.answer)
        return output


def _should_use_fallback(
    exc: QwenChatRunnerError,
    fallback_model: str | None,
    primary_model: str,
) -> bool:
    if fallback_model is None or not fallback_model.strip():
        return False
    if fallback_model.strip() == primary_model:
        return False
    text = str(exc).lower()
    return (
        "429" in text
        or "rate limit" in text
        or "status 5" in text
        or "failed before receiving" in text
    )


@dataclass(slots=True)
class QwenHTTPChatClient:
    """Cliente HTTP pequeno para chat completions Qwen/OpenAI-compatible."""

    api_key: str = field(repr=False)
    base_url: str
    timeout_seconds: float
    max_retries: int
    transport: httpx.BaseTransport | None = None
    usage_tracker: ProviderUsageTracker | None = None
    provider_name: str = "qwen"
    price_catalog: ProviderPriceCatalog = ProviderPriceCatalog()
    budget_guard: ProviderBudgetGuard | None = None
    # Interactive chat should fail fast under rate limits (default ≤12s budget).
    max_retry_budget_seconds: float = 12.0
    _cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)
    _active_client: httpx.Client | None = field(default=None, repr=False)

    def set_cancel_event(self, event: threading.Event) -> None:
        self._cancel_event = event

    def request_cancel(self) -> None:
        self._cancel_event.set()
        client = self._active_client
        if client is not None:
            try:
                client.close()
            except Exception:  # noqa: BLE001 — best-effort cancel
                pass

    def create_chat_completion(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        tools: list[ChatToolDefinition] | None = None,
        on_answer_delta: Callable[[str], None] | None = None,
    ) -> ChatCompletionResponse:
        if self._cancel_event.is_set():
            raise QwenChatRunnerError("qwen chat request canceled")
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0,
            # Bailian/Qwen thinking models reject object tool_choice (HTTP 400)
            # and often wrap final answers in non-JSON reasoning channels.
            # RAG tool-calling + JSON answer contract require non-thinking turns.
            "enable_thinking": False,
        }
        if tools is not None:
            payload["tools"] = tools
            payload["tool_choice"] = _tool_choice(tools)
        else:
            # Final answer turn: force machine-parseable JSON object contract.
            payload["response_format"] = {"type": "json_object"}
            if on_answer_delta is not None:
                payload["stream"] = True

        started = perf_counter()
        try:
            if tools is None and on_answer_delta is not None:
                response_data, request_id = self._post_stream(
                    endpoint=_chat_endpoint(self.base_url),
                    payload=payload,
                    on_answer_delta=on_answer_delta,
                )
            else:
                response_data, request_id = self._post(
                    endpoint=_chat_endpoint(self.base_url),
                    payload=payload,
                )
            record = build_success_record(
                provider=self.provider_name,
                model=model,
                operation="chat",
                duration_ms=_elapsed_ms(started),
                response_data=response_data,
                price_catalog=self.price_catalog,
                request_id=request_id,
            )
            record_with_budget(
                record=record,
                tracker=self.usage_tracker,
                budget_guard=self.budget_guard,
            )
            return response_data
        except Exception as exc:
            if not isinstance(exc, ProviderBudgetExceededError):
                self._record_failure(
                    model=model,
                    duration_ms=_elapsed_ms(started),
                    error=exc,
                )
            raise

    def _post(
        self,
        *,
        endpoint: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], str | None]:
        from time import sleep

        last_error: Exception | None = None
        # Cap interactive retries: at most 2 attempts (1 retry) for chat UX.
        attempts = min(max(0, self.max_retries), 1) + 1
        budget_started = perf_counter()
        for attempt in range(attempts):
            if self._cancel_event.is_set():
                raise QwenChatRunnerError("qwen chat request canceled")
            try:
                with httpx.Client(
                    timeout=self.timeout_seconds,
                    transport=self.transport,
                ) as client:
                    self._active_client = client
                    try:
                        response = client.post(
                            endpoint,
                            headers={
                                "Authorization": f"Bearer {self.api_key}",
                                "Content-Type": "application/json",
                            },
                            json=payload,
                        )
                    finally:
                        self._active_client = None
                retryable = response.status_code >= 500 or response.status_code == 429
                if retryable and attempt < attempts - 1:
                    sleep_s = _retry_backoff_seconds(response, attempt=attempt)
                    if (
                        perf_counter() - budget_started + sleep_s
                        > self.max_retry_budget_seconds
                    ):
                        raise QwenChatRunnerError(
                            f"qwen chat request failed with status {response.status_code}"
                        )
                    sleep(sleep_s)
                    continue
                if response.status_code >= 400:
                    raise QwenChatRunnerError(
                        f"qwen chat request failed with status {response.status_code}"
                    )
                data = response.json()
                if not isinstance(data, dict):
                    raise QwenChatRunnerError(
                        "qwen chat response must be a JSON object"
                    )
                return data, _response_request_id(response)
            except QwenChatRunnerError:
                raise
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if self._cancel_event.is_set():
                    raise QwenChatRunnerError("qwen chat request canceled") from exc
                last_error = exc
                if attempt < attempts - 1:
                    sleep_s = _retry_backoff_seconds(None, attempt=attempt)
                    if (
                        perf_counter() - budget_started + sleep_s
                        > self.max_retry_budget_seconds
                    ):
                        break
                    sleep(sleep_s)
                    continue
                break

        raise QwenChatRunnerError(
            "qwen chat request failed before receiving a response"
        ) from last_error

    def _post_stream(
        self,
        *,
        endpoint: str,
        payload: dict[str, Any],
        on_answer_delta: Callable[[str], None],
    ) -> tuple[dict[str, Any], str | None]:
        """Stream a final (no-tools) completion and emit progressive answer text."""

        from time import sleep

        if self._cancel_event.is_set():
            raise QwenChatRunnerError("qwen chat request canceled")
        attempts = min(max(0, self.max_retries), 1) + 1
        budget_started = perf_counter()
        last_error: Exception | None = None
        for attempt in range(attempts):
            if self._cancel_event.is_set():
                raise QwenChatRunnerError("qwen chat request canceled")
            content_parts: list[str] = []
            request_id: str | None = None
            emitted_answer = ""
            try:
                with httpx.Client(
                    timeout=self.timeout_seconds,
                    transport=self.transport,
                ) as client:
                    self._active_client = client
                    try:
                        with client.stream(
                            "POST",
                            endpoint,
                            headers={
                                "Authorization": f"Bearer {self.api_key}",
                                "Content-Type": "application/json",
                            },
                            json=payload,
                        ) as response:
                            if response.status_code >= 400:
                                body = response.read()
                                _ = body
                                retryable = (
                                    response.status_code >= 500
                                    or response.status_code == 429
                                )
                                if retryable and attempt < attempts - 1:
                                    sleep_s = _retry_backoff_seconds(
                                        response, attempt=attempt
                                    )
                                    if (
                                        perf_counter() - budget_started + sleep_s
                                        > self.max_retry_budget_seconds
                                    ):
                                        raise QwenChatRunnerError(
                                            "qwen chat request failed with status "
                                            f"{response.status_code}"
                                        )
                                    sleep(sleep_s)
                                    continue
                                raise QwenChatRunnerError(
                                    "qwen chat request failed with status "
                                    f"{response.status_code}"
                                )
                            request_id = _response_request_id(response)
                            for line in response.iter_lines():
                                if self._cancel_event.is_set():
                                    raise QwenChatRunnerError(
                                        "qwen chat request canceled"
                                    )
                                if not line:
                                    continue
                                if line.startswith("data:"):
                                    data_str = line[5:].strip()
                                else:
                                    continue
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data_str)
                                except json.JSONDecodeError:
                                    continue
                                if not isinstance(chunk, dict):
                                    continue
                                delta_text = _stream_chunk_text(chunk)
                                if delta_text:
                                    content_parts.append(delta_text)
                                    partial = _partial_answer_from_json_buffer(
                                        "".join(content_parts)
                                    )
                                    if partial is not None and len(partial) > len(
                                        emitted_answer
                                    ):
                                        piece = partial[len(emitted_answer) :]
                                        emitted_answer = partial
                                        on_answer_delta(piece)
                    finally:
                        self._active_client = None
            except QwenChatRunnerError:
                raise
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if self._cancel_event.is_set():
                    raise QwenChatRunnerError("qwen chat request canceled") from exc
                last_error = exc
                if attempt < attempts - 1:
                    sleep_s = _retry_backoff_seconds(None, attempt=attempt)
                    if (
                        perf_counter() - budget_started + sleep_s
                        > self.max_retry_budget_seconds
                    ):
                        break
                    sleep(sleep_s)
                    continue
                break

            full_content = "".join(content_parts)
            if not full_content.strip():
                raise QwenChatRunnerError("qwen chat stream returned empty content")
            return (
                {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": full_content,
                            }
                        }
                    ]
                },
                request_id,
            )

        raise QwenChatRunnerError(
            "qwen chat request failed before receiving a response"
        ) from last_error

    def _record_failure(
        self,
        *,
        model: str,
        duration_ms: int,
        error: Exception,
    ) -> None:
        if self.usage_tracker is None:
            return
        self.usage_tracker.record(
            build_failure_record(
                provider=self.provider_name,
                model=model,
                operation="chat",
                duration_ms=duration_ms,
                error=error,
            )
        )


def _stream_chunk_text(chunk: dict[str, Any]) -> str:
    choices = chunk.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    delta = first.get("delta")
    if isinstance(delta, dict):
        content = delta.get("content")
        if isinstance(content, str):
            return content
    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
    return ""


def _partial_answer_from_json_buffer(buffer: str) -> str | None:
    """Extract progressive answer text from a partial JSON object stream."""

    match = re.search(r'"answer"\s*:\s*"', buffer)
    if match is None:
        return None
    index = match.end()
    chars: list[str] = []
    while index < len(buffer):
        char = buffer[index]
        if char == "\\" and index + 1 < len(buffer):
            escape = buffer[index + 1]
            if escape == "n":
                chars.append("\n")
            elif escape == "t":
                chars.append("\t")
            elif escape == '"':
                chars.append('"')
            elif escape == "\\":
                chars.append("\\")
            else:
                chars.append(escape)
            index += 2
            continue
        if char == '"':
            break
        chars.append(char)
        index += 1
    return "".join(chars)


def _initial_messages(request: ChatRunnerRequest) -> list[ChatMessage]:
    system_content = (
        "You are Adaptive RAG's retrieval-grounded chat runner. "
        "You MUST call retrieval_search before answering factual or "
        "project-knowledge questions. If retrieval returns no useful "
        "evidence, say you could not find sources and keep "
        "cited_chunk_ids empty. Never invent chunk ids or unsupported "
        "facts. Prefer the retrieval query when provided in the latest "
        "user turn metadata. When the user explicitly asks to save, learn, "
        "remember, or capture project knowledge, call commit_knowledge. "
        "Choose scope=message when the knowledge is only in the latest "
        "user message, or scope=session when it summarizes this chat "
        "session. If the user asks to change an existing knowledge "
        "draft card, call refine_knowledge with its draft_id and the "
        "revised knowledge_text. If the user explicitly confirms saving "
        "a draft card, call approve_knowledge with its draft_id. If the "
        "user asks to discard a draft card, call cancel_knowledge. "
        "Return only a JSON object with keys answer and cited_chunk_ids. "
        "cited_chunk_ids must contain only chunk_id values returned by "
        "retrieval_search."
    )
    if request.user_memory and request.user_memory.strip():
        system_content = f"{system_content}\n\n{request.user_memory.strip()}"
    messages: list[ChatMessage] = [
        {
            "role": "system",
            "content": system_content,
        },
    ]
    for turn in request.history:
        if turn.role in {"user", "assistant"} and turn.content.strip():
            messages.append({"role": turn.role, "content": turn.content})
    user_content = request.message
    if request.retrieval_query and request.retrieval_query != request.message:
        user_content = (
            f"{request.message}\n\n[retrieval_query] {request.retrieval_query}"
        )
    messages.append({"role": "user", "content": user_content})
    return messages


def _tool_schemas(tools: ChatTools) -> list[ChatToolDefinition]:
    schemas = [_retrieval_tool_schema()]
    if tools.knowledge is not None:
        schemas.extend(
            [
                _knowledge_proposal_tool_schema(),
                _knowledge_refinement_tool_schema(),
                _knowledge_cancellation_tool_schema(),
                _knowledge_approval_tool_schema(),
            ]
        )
    return schemas


def _retrieval_tool_schema() -> ChatToolDefinition:
    return {
        "type": "function",
        "function": {
            "name": _RETRIEVAL_TOOL_NAME,
            "description": (
                "Search indexed project evidence. Returns candidate chunks "
                "with citation metadata and chunk_id values that may be cited."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for project evidence.",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "description": (
                            "Maximum result count. It is capped by the user "
                            "request retrieval_limit."
                        ),
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    }


def _knowledge_proposal_tool_schema() -> ChatToolDefinition:
    return {
        "type": "function",
        "function": {
            "name": _KNOWLEDGE_PROPOSAL_TOOL_NAME,
            "description": (
                "Create or refine an auditable project knowledge draft card "
                "when the user explicitly asks to save, learn, remember, or "
                "capture knowledge from the chat."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "knowledge_text": {
                        "type": "string",
                        "description": (
                            "The exact project knowledge text that should be "
                            "shown in the review card."
                        ),
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["message", "session"],
                        "description": (
                            "Use message for the latest user message, or "
                            "session for a synthesis of the current chat."
                        ),
                    },
                    "draft_id": {
                        "type": "string",
                        "description": (
                            "Existing draft id to refine when the user refers "
                            "to a specific knowledge card."
                        ),
                    },
                },
                "required": ["knowledge_text", "scope"],
                "additionalProperties": False,
            },
        },
    }


def _knowledge_refinement_tool_schema() -> ChatToolDefinition:
    return {
        "type": "function",
        "function": {
            "name": _KNOWLEDGE_REFINEMENT_TOOL_NAME,
            "description": (
                "Update an existing project knowledge draft card when the user "
                "asks to modify, correct, shorten, expand, or refine it. Keep "
                "the same draft_id and provide the revised knowledge text."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id": {
                        "type": "string",
                        "description": "Existing knowledge draft id to update.",
                    },
                    "knowledge_text": {
                        "type": "string",
                        "description": (
                            "The revised project knowledge text to show in the "
                            "same review card."
                        ),
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["message", "session"],
                        "description": (
                            "Use message for latest-message knowledge, or "
                            "session when the revised draft summarizes the chat."
                        ),
                    },
                },
                "required": ["draft_id", "knowledge_text"],
                "additionalProperties": False,
            },
        },
    }


def _knowledge_cancellation_tool_schema() -> ChatToolDefinition:
    return {
        "type": "function",
        "function": {
            "name": _KNOWLEDGE_CANCELLATION_TOOL_NAME,
            "description": (
                "Cancel pending knowledge draft cards when the user asks to "
                "discard or cancel them. Pass draft_id for a specific card; omit "
                "it only when the user clearly wants every pending draft removed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id": {
                        "type": "string",
                        "description": "Knowledge draft id to cancel.",
                    },
                },
                "additionalProperties": False,
            },
        },
    }


def _knowledge_approval_tool_schema() -> ChatToolDefinition:
    return {
        "type": "function",
        "function": {
            "name": _KNOWLEDGE_APPROVAL_TOOL_NAME,
            "description": (
                "Approve or request approval for an existing knowledge draft "
                "only after the user explicitly confirms saving that card."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id": {
                        "type": "string",
                        "description": "Knowledge draft id to approve.",
                    },
                },
                "required": ["draft_id"],
                "additionalProperties": False,
            },
        },
    }


def _tool_choice(tools: list[ChatToolDefinition]) -> str | dict[str, Any]:
    if not tools:
        raise QwenChatRunnerError("qwen chat tools must not be empty")
    if len(tools) > 1:
        return "auto"
    function = tools[0].get("function")
    if not isinstance(function, dict) or not isinstance(function.get("name"), str):
        raise QwenChatRunnerError("qwen chat tool is missing function name")
    return {
        "type": "function",
        "function": {"name": function["name"]},
    }


def _first_message(response: ChatCompletionResponse) -> ChatMessage:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise QwenChatRunnerError("qwen chat response is missing choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise QwenChatRunnerError("qwen chat choice must be a JSON object")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise QwenChatRunnerError("qwen chat choice is missing message")
    return message


def _tool_calls(message: ChatMessage) -> list[dict[str, Any]]:
    value = message.get("tool_calls")
    if value is None:
        return []
    if not isinstance(value, list):
        raise QwenChatRunnerError("qwen chat tool_calls must be a list")
    calls: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise QwenChatRunnerError("qwen chat tool call must be a JSON object")
        calls.append(item)
    return calls


def _assistant_tool_call_message(
    message: ChatMessage,
    tool_calls: list[dict[str, Any]],
) -> ChatMessage:
    return {
        "role": "assistant",
        "content": message.get("content"),
        "tool_calls": tool_calls,
    }


def _execute_tool_call(
    tool_call: dict[str, Any],
    *,
    request: ChatRunnerRequest,
    tools: ChatTools,
) -> ChatRetrievalToolResult | Mapping[str, object]:
    function = tool_call.get("function")
    if not isinstance(function, dict):
        raise QwenChatRunnerError("qwen chat tool call is missing function")
    name = function.get("name")
    arguments = _tool_arguments(function.get("arguments"))
    if name in {
        _KNOWLEDGE_PROPOSAL_TOOL_NAME,
        _KNOWLEDGE_REFINEMENT_TOOL_NAME,
        _KNOWLEDGE_CANCELLATION_TOOL_NAME,
        _KNOWLEDGE_APPROVAL_TOOL_NAME,
    }:
        if tools.knowledge is None:
            raise QwenChatRunnerError("qwen knowledge proposal tool is unavailable")
        if name == _KNOWLEDGE_CANCELLATION_TOOL_NAME:
            draft_id = arguments.get("draft_id")
            if draft_id is not None and not isinstance(draft_id, str):
                raise QwenChatRunnerError(
                    "qwen chat knowledge draft_id must be a string"
                )
            return tools.knowledge.cancel(draft_id=draft_id)
        if name == _KNOWLEDGE_APPROVAL_TOOL_NAME:
            draft_id = arguments.get("draft_id")
            if not isinstance(draft_id, str) or not draft_id.strip():
                raise QwenChatRunnerError(
                    "qwen chat knowledge draft_id must be a non-empty string"
                )
            return tools.knowledge.approve(draft_id=draft_id)
        knowledge_text = arguments.get("knowledge_text")
        if not isinstance(knowledge_text, str) or not knowledge_text.strip():
            raise QwenChatRunnerError(
                "qwen chat knowledge_text must be a non-empty string"
            )
        scope = arguments.get("scope", "message")
        if not isinstance(scope, str) or not scope.strip():
            raise QwenChatRunnerError("qwen chat knowledge scope must be a string")
        draft_id = arguments.get("draft_id")
        if draft_id is not None and (
            not isinstance(draft_id, str) or not draft_id.strip()
        ):
            raise QwenChatRunnerError(
                "qwen chat knowledge draft_id must be a non-empty string"
            )
        if name == _KNOWLEDGE_REFINEMENT_TOOL_NAME:
            if not isinstance(draft_id, str):
                raise QwenChatRunnerError(
                    "qwen chat knowledge draft_id must be a non-empty string"
                )
            return tools.knowledge.refine(
                draft_id=draft_id,
                knowledge_text=knowledge_text,
                scope=scope,
            )
        return tools.knowledge.commit(
            knowledge_text=knowledge_text,
            scope=scope,
            draft_id=draft_id,
        )
    if name != _RETRIEVAL_TOOL_NAME:
        raise QwenChatRunnerError(f"unsupported qwen chat tool call: {name}")
    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip():
        raise QwenChatRunnerError("qwen chat retrieval query must be a string")
    return tools.retrieval.search(
        query=query.strip(),
        limit=_capped_limit(arguments.get("limit"), request.retrieval_limit),
        metadata_filter=request.metadata_filter,
    )


def _tool_arguments(value: object) -> dict[str, Any]:
    if not isinstance(value, str):
        raise QwenChatRunnerError("qwen chat tool arguments must be a JSON string")
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise QwenChatRunnerError(
            "qwen chat tool arguments must be valid JSON"
        ) from exc
    if not isinstance(parsed, dict):
        raise QwenChatRunnerError("qwen chat tool arguments must be a JSON object")
    return parsed


def _capped_limit(value: object, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise QwenChatRunnerError("qwen chat retrieval limit must be positive")
    return min(value, default)


def _tool_result_message(
    tool_call: dict[str, Any],
    result: ChatRetrievalToolResult | Mapping[str, object],
) -> ChatMessage:
    if isinstance(result, ChatRetrievalToolResult):
        content: object = {"results": list(result.results)}
    else:
        content = dict(result)
    return {
        "role": "tool",
        "tool_call_id": _tool_call_id(tool_call),
        "content": json.dumps(content, sort_keys=True),
    }


def _tool_call_id(tool_call: dict[str, Any]) -> str:
    value = tool_call.get("id")
    if not isinstance(value, str) or not value:
        raise QwenChatRunnerError("qwen chat tool call is missing id")
    return value


_THINK_TAG_RE = re.compile(
    r"<think>[\s\S]*?</think>|<thinking>[\s\S]*?</thinking>",
    re.IGNORECASE,
)
_FENCED_JSON_RE = re.compile(
    r"```(?:json)?\s*([\s\S]*?)```",
    re.IGNORECASE,
)


def _message_content(message: ChatMessage) -> str:
    content = message.get("content")
    text = _coerce_text_content(content)
    if text is None or not text.strip():
        raise QwenChatRunnerError("qwen chat response content must be a JSON object")
    return text


def _coerce_text_content(content: object) -> str | None:
    """Normalize OpenAI-compatible content (string or text parts) to plain text."""

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str) and item.strip():
                parts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text)
                continue
            # Some providers use content parts with type/content keys.
            nested = item.get("content")
            if isinstance(nested, str) and nested.strip():
                parts.append(nested)
        if parts:
            return "".join(parts)
    return None


def _parse_runner_output(content: str) -> ChatRunnerOutput:
    parsed = _loads_json_object(content)

    answer = parsed.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise QwenChatRunnerError("qwen chat response answer must be a string")

    raw_ids = parsed.get("cited_chunk_ids", [])
    if not isinstance(raw_ids, list):
        raise QwenChatRunnerError("qwen chat cited_chunk_ids must be a list")

    cited_chunk_ids: list[UUID] = []
    for raw_id in raw_ids:
        if not isinstance(raw_id, str):
            raise QwenChatRunnerError("qwen chat cited chunk id must be a string")
        try:
            cited_chunk_ids.append(UUID(raw_id))
        except ValueError as exc:
            raise QwenChatRunnerError(
                f"qwen chat cited chunk id is not a UUID: {raw_id}"
            ) from exc

    return ChatRunnerOutput(
        answer=answer.strip(),
        cited_chunk_ids=tuple(cited_chunk_ids),
    )


def _loads_json_object(content: str) -> dict[str, Any]:
    """Parse the JSON answer contract from model text with production fallbacks.

    Qwen/Bailian models sometimes wrap the required object in markdown fences,
    preambles, or residual think tags even when asked for JSON only.
    """

    text = _THINK_TAG_RE.sub("", content).strip()
    if not text:
        raise QwenChatRunnerError("qwen chat response content must be a JSON object")

    for candidate in _json_object_candidates(text):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    extracted = _extract_first_json_object(text)
    if extracted is not None:
        return extracted

    raise QwenChatRunnerError("qwen chat response content must be a JSON object")


def _json_object_candidates(text: str) -> list[str]:
    candidates = [text]
    for match in _FENCED_JSON_RE.finditer(text):
        fenced = match.group(1).strip()
        if fenced:
            candidates.append(fenced)
    return candidates


def _extract_first_json_object(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            parsed, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _chat_endpoint(base_url: str) -> str:
    value = base_url.rstrip("/")
    if value.endswith("/chat/completions"):
        return value
    return f"{value}/chat/completions"


def _response_request_id(response: httpx.Response) -> str | None:
    for header_name in ("x-request-id", "x-acs-request-id", "request-id"):
        value = response.headers.get(header_name)
        if value is not None:
            return str(value)
    return None


def _retry_backoff_seconds(
    response: httpx.Response | None,
    *,
    attempt: int,
) -> float:
    """Backoff for transport/5xx/429 retries. Honors Retry-After when present."""

    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return max(0.0, min(float(retry_after), 30.0))
            except ValueError:
                pass
    # attempt 0 → 0.5s, 1 → 1s, 2 → 2s (capped)
    return min(0.5 * (2**attempt), 8.0)


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))
