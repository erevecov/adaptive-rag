"""In-process registry of versioned, typed job handlers."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field

from pydantic import BaseModel

from adaptive_rag.db.models.user import WORKSPACE_ROLE_VALUES
from adaptive_rag.jobs.errors import (
    InvalidJobResultError,
    JobPlatformError,
    JobResultTooLargeError,
    UnknownJobHandlerError,
)
from adaptive_rag.jobs.types import (
    MAX_PAYLOAD_BYTES,
    MAX_RESULT_BYTES,
    ConcurrencyPolicy,
    HandlerKey,
    JobContext,
    JobScope,
    RetryPolicy,
    ensure_json_size,
    redact_error_message,
    redact_secret_keys,
    reject_secret_material,
)

type JobHandler = Callable[[JobContext, BaseModel], object | Awaitable[object]]
type Redactor = Callable[[object], object]
type ConcurrencyKeyFactory = Callable[[BaseModel], str | None]

_SLUG_PATTERN = re.compile(r"[a-z][a-z0-9_-]{0,99}\Z")
_ROLE_RANK = {role: index for index, role in enumerate(reversed(WORKSPACE_ROLE_VALUES))}
_ROLE_RANK["superadmin"] = len(_ROLE_RANK)


@dataclass(frozen=True, slots=True)
class JobHandlerDefinition:
    name: str
    version: int
    payload_model: type[BaseModel]
    handler: JobHandler
    queue_name: str
    default_priority: int = 0
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    lease_seconds: int | None = None
    concurrency: ConcurrencyPolicy = field(default_factory=ConcurrencyPolicy)
    concurrency_key: ConcurrencyKeyFactory | None = None
    allowed_scopes: frozenset[JobScope] = frozenset({"workspace"})
    allow_manual_enqueue: bool = False
    minimum_manual_role: str = "admin"
    redact_payload: Redactor = redact_secret_keys
    redact_result: Redactor = redact_secret_keys
    redact_error: Redactor = redact_error_message

    @property
    def key(self) -> HandlerKey:
        return (self.name, self.version)


class JobRegistry:
    """Rejects dynamic handlers and validates every payload before enqueue."""

    def __init__(self) -> None:
        self._definitions: dict[HandlerKey, JobHandlerDefinition] = {}

    @property
    def supported_handlers(self) -> frozenset[HandlerKey]:
        return frozenset(self._definitions)

    def register(self, definition: JobHandlerDefinition) -> None:
        self._validate_definition(definition)
        if definition.key in self._definitions:
            raise ValueError(
                f"Job handler {definition.name}@{definition.version} "
                "is already registered"
            )
        self._definitions[definition.key] = definition

    def get(self, name: str, version: int) -> JobHandlerDefinition:
        try:
            return self._definitions[(name, version)]
        except KeyError as exc:
            raise UnknownJobHandlerError(name, version) from exc

    def validate_payload(
        self, name: str, version: int, raw: Mapping[str, object]
    ) -> BaseModel:
        definition = self.get(name, version)
        reject_secret_material(raw)
        payload = definition.payload_model.model_validate(raw)
        reject_secret_material(payload.model_dump(mode="python"))
        ensure_json_size(payload.model_dump(mode="json"), limit_bytes=MAX_PAYLOAD_BYTES)
        return payload

    def validate_result(self, name: str, version: int, result: object) -> object:
        definition = self.get(name, version)
        try:
            redacted = definition.redact_result(result)
            ensure_json_size(
                redacted,
                limit_bytes=MAX_RESULT_BYTES,
                error_type=JobResultTooLargeError,
            )
        except JobPlatformError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalize plugin output failures
            raise InvalidJobResultError("job result validation failed") from exc
        return redacted

    def manual_definitions(
        self, *, minimum_role: str
    ) -> tuple[JobHandlerDefinition, ...]:
        if minimum_role not in _ROLE_RANK:
            raise ValueError(f"Unknown workspace role: {minimum_role}")
        available = (
            definition
            for definition in self._definitions.values()
            if definition.allow_manual_enqueue
            and "workspace" in definition.allowed_scopes
            and _ROLE_RANK[minimum_role] >= _ROLE_RANK[definition.minimum_manual_role]
        )
        return tuple(sorted(available, key=lambda item: item.key))

    @staticmethod
    def _validate_definition(definition: JobHandlerDefinition) -> None:
        if _SLUG_PATTERN.fullmatch(definition.name) is None:
            raise ValueError("Handler name must be a bounded lowercase slug")
        if _SLUG_PATTERN.fullmatch(definition.queue_name) is None:
            raise ValueError("Queue name must be a bounded lowercase slug")
        if definition.version <= 0:
            raise ValueError("Handler version must be positive")
        if not -1000 <= definition.default_priority <= 1000:
            raise ValueError("Handler priority must be within [-1000, 1000]")
        if definition.lease_seconds is not None and not (
            15 <= definition.lease_seconds <= 3600
        ):
            raise ValueError("Handler lease must be within [15, 3600] seconds")
        policy = definition.retry_policy
        if not 0 <= policy.max_retries <= 25:
            raise ValueError("Automatic retries must be within [0, 25]")
        if policy.base_delay_seconds <= 0 or policy.max_delay_seconds <= 0:
            raise ValueError("Retry delays must be positive")
        if policy.base_delay_seconds > policy.max_delay_seconds:
            raise ValueError("Base retry delay cannot exceed maximum delay")
        for value in (
            definition.concurrency.handler_limit,
            definition.concurrency.key_limit,
        ):
            if value is not None and value <= 0:
                raise ValueError("Concurrency limits must be positive")
        if not definition.allowed_scopes or not definition.allowed_scopes <= {
            "workspace",
            "system",
        }:
            raise ValueError("Handler scopes must contain workspace and/or system")
        if definition.minimum_manual_role not in WORKSPACE_ROLE_VALUES:
            raise ValueError("Unknown minimum workspace role")
