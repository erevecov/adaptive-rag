"""Runner live de chat Qwen sobre endpoint OpenAI-compatible."""

from __future__ import annotations

import json
from collections.abc import Mapping
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
    ) -> ChatCompletionResponse:
        """Ejecuta una llamada chat completion compatible con OpenAI."""


@dataclass(slots=True)
class QwenChatRunner:
    """Implementa ChatRunner usando Qwen con tool calling de retrieval."""

    model_name: str
    client: QwenChatClient
    provider_name: str = "qwen"

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        messages = _initial_messages(request)
        first_response = self.client.create_chat_completion(
            model=self.model_name,
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
                model=self.model_name,
                messages=messages,
            )
            final_message = _first_message(final_response)
            return _parse_runner_output(_message_content(final_message))

        return _parse_runner_output(_message_content(first_message))


@dataclass(frozen=True, slots=True)
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

    def create_chat_completion(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        tools: list[ChatToolDefinition] | None = None,
    ) -> ChatCompletionResponse:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0,
        }
        if tools is not None:
            payload["tools"] = tools
            payload["tool_choice"] = _tool_choice(tools)
        started = perf_counter()
        try:
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
        last_error: Exception | None = None
        attempts = max(0, self.max_retries) + 1
        for attempt in range(attempts):
            try:
                with httpx.Client(
                    timeout=self.timeout_seconds,
                    transport=self.transport,
                ) as client:
                    response = client.post(
                        endpoint,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                if response.status_code >= 500 and attempt < attempts - 1:
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
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt < attempts - 1:
                    continue
                break

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


def _initial_messages(request: ChatRunnerRequest) -> list[ChatMessage]:
    return [
        {
            "role": "system",
            "content": (
                "You are Adaptive RAG's retrieval-grounded chat runner. "
                "Use the retrieval_search tool before answering when evidence "
                "is needed. When the user explicitly asks to save, learn, "
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
            ),
        },
        {
            "role": "user",
            "content": request.message,
        },
    ]


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


def _message_content(message: ChatMessage) -> str:
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise QwenChatRunnerError(
            "qwen chat response content must be a JSON object"
        )
    return content


def _parse_runner_output(content: str) -> ChatRunnerOutput:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise QwenChatRunnerError(
            "qwen chat response content must be a JSON object"
        ) from exc
    if not isinstance(parsed, dict):
        raise QwenChatRunnerError(
            "qwen chat response content must be a JSON object"
        )

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


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))
