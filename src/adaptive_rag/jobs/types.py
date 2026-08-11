"""Pure job-platform limits, retry math, redaction, and handler context."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import SecretBytes, SecretStr

from adaptive_rag.jobs.errors import (
    JobCancelled,
    JobPayloadTooLargeError,
    JobPlatformError,
    JobProgressTooLargeError,
    JobSecretMaterialError,
)

JobScope = Literal["workspace", "system"]
HandlerKey = tuple[str, int]

MAX_PAYLOAD_BYTES = 256 * 1024
MAX_RESULT_BYTES = 64 * 1024
MAX_PROGRESS_BYTES = 8 * 1024
MAX_EVENT_METADATA_BYTES = 16 * 1024
MAX_SAFE_ERROR_BYTES = 4 * 1024

_SECRET_KEYS = {
    "password",
    "secret",
    "token",
    "api_key",
    "authorization",
    "private_key",
}
_SECRET_SUFFIXES = ("_password", "_secret", "_token")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0


@dataclass(frozen=True, slots=True)
class ConcurrencyPolicy:
    handler_limit: int | None = None
    key_limit: int | None = None


def is_secret_key(key: str) -> bool:
    normalized = key.casefold()
    return normalized in _SECRET_KEYS or normalized.endswith(_SECRET_SUFFIXES)


def reject_secret_material(value: object, *, path: str = "payload") -> None:
    """Reject raw secret fields and Pydantic secret values before persistence."""

    if isinstance(value, (SecretStr, SecretBytes)):
        raise JobSecretMaterialError(f"Secret value is not allowed at {path}")
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if is_secret_key(key_text):
                raise JobSecretMaterialError(
                    f"Secret field is not allowed at {path}.{key_text}"
                )
            reject_secret_material(child, path=f"{path}.{key_text}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            reject_secret_material(child, path=f"{path}[{index}]")


def canonical_json_bytes(value: object) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Value must be JSON serializable") from exc
    return rendered.encode("utf-8")


def ensure_json_size(
    value: object,
    *,
    limit_bytes: int,
    error_type: type[JobPlatformError] = JobPayloadTooLargeError,
) -> int:
    size = len(canonical_json_bytes(value))
    if size > limit_bytes:
        raise error_type(f"Serialized JSON is {size} bytes; limit is {limit_bytes}")
    return size


def redact_secret_keys(value: object) -> object:
    """Return a recursively redacted JSON-compatible copy."""

    if isinstance(value, Mapping):
        return {
            str(key): (
                "[REDACTED]" if is_secret_key(str(key)) else redact_secret_keys(child)
            )
            for key, child in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_secret_keys(child) for child in value]
    if isinstance(value, (SecretStr, SecretBytes)):
        return "[REDACTED]"
    return value


def redact_error_message(value: object) -> object:
    message = (
        value.public_message
        if isinstance(value, JobPlatformError)
        else "job handler failed; see trace ID"
    )
    return truncate_utf8(message, limit_bytes=MAX_SAFE_ERROR_BYTES)


def truncate_utf8(value: str, *, limit_bytes: int) -> str:
    if limit_bytes < 0:
        raise ValueError("limit_bytes must be non-negative")
    return value.encode("utf-8")[:limit_bytes].decode("utf-8", errors="ignore")


def retry_delay_seconds(
    policy: RetryPolicy, retry_count: int, *, random_value: float
) -> float:
    if retry_count < 0:
        raise ValueError("retry_count must be non-negative")
    if not 0.0 <= random_value <= 1.0:
        raise ValueError("random_value must be within [0, 1]")
    upper: float = min(
        float(policy.max_delay_seconds),
        float(policy.base_delay_seconds * (2**retry_count)),
    )
    return random_value * upper


@dataclass(frozen=True, slots=True)
class JobContext:
    job_id: UUID
    attempt_id: UUID
    workspace_id: UUID | None
    idempotency_key: str | None
    is_cancel_requested_callback: Callable[[], bool]
    report_progress_callback: Callable[[dict[str, object]], None]
    is_lease_healthy_callback: Callable[[], bool]

    def is_cancel_requested(self) -> bool:
        return self.is_cancel_requested_callback()

    def raise_if_cancelled(self) -> None:
        if self.is_cancel_requested():
            raise JobCancelled("Cancellation was requested")

    def report_progress(self, progress: Mapping[str, object]) -> None:
        snapshot = dict(progress)
        reject_secret_material(snapshot, path="progress")
        ensure_json_size(
            snapshot,
            limit_bytes=MAX_PROGRESS_BYTES,
            error_type=JobProgressTooLargeError,
        )
        self.report_progress_callback(snapshot)

    def is_lease_healthy(self) -> bool:
        return self.is_lease_healthy_callback()
