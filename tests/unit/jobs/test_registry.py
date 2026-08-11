"""Behavioral contract for code-registered background-job handlers."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict, SecretStr

from adaptive_rag.jobs import (
    ConcurrencyPolicy,
    JobHandlerDefinition,
    JobPayloadTooLargeError,
    JobRegistry,
    JobResultTooLargeError,
    JobSecretMaterialError,
    RetryPolicy,
    UnknownJobHandlerError,
)


class EchoPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


class SecretPayload(BaseModel):
    credential: SecretStr


def echo_handler(_context, payload: EchoPayload) -> dict[str, str]:
    return {"echo": payload.message}


def echo_definition(**overrides) -> JobHandlerDefinition:
    values = {
        "name": "echo",
        "version": 1,
        "payload_model": EchoPayload,
        "handler": echo_handler,
        "queue_name": "default",
        "allow_manual_enqueue": True,
        "minimum_manual_role": "admin",
    }
    values.update(overrides)
    return JobHandlerDefinition(**values)


def test_registry_validates_payload_and_manual_role() -> None:
    registry = JobRegistry()
    registry.register(echo_definition())

    payload = registry.validate_payload("echo", 1, {"message": "hello"})

    assert payload == EchoPayload(message="hello")
    assert registry.get("echo", 1).minimum_manual_role == "admin"
    assert registry.manual_definitions(minimum_role="admin") == (
        registry.get("echo", 1),
    )
    assert registry.supported_handlers == frozenset({("echo", 1)})


def test_registry_rejects_unknown_or_duplicate_handler() -> None:
    registry = JobRegistry()
    registry.register(echo_definition())

    with pytest.raises(UnknownJobHandlerError):
        registry.validate_payload("payload.module:callable", 1, {})
    with pytest.raises(ValueError, match="already registered"):
        registry.register(echo_definition())


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "module:callable"},
        {"version": 0},
        {"queue_name": "Not Valid"},
        {"default_priority": 1001},
        {"lease_seconds": 14},
        {"retry_policy": RetryPolicy(max_retries=26)},
        {"concurrency": ConcurrencyPolicy(handler_limit=0)},
        {"allowed_scopes": frozenset()},
        {"minimum_manual_role": "owner"},
    ],
)
def test_registry_rejects_invalid_handler_definitions(overrides) -> None:
    with pytest.raises(ValueError):
        JobRegistry().register(echo_definition(**overrides))


def test_registry_rejects_oversized_payload_after_json_serialization() -> None:
    class LargePayload(BaseModel):
        data: str

    registry = JobRegistry()
    registry.register(
        echo_definition(
            name="large", payload_model=LargePayload, handler=lambda c, p: None
        )
    )

    with pytest.raises(JobPayloadTooLargeError):
        registry.validate_payload("large", 1, {"data": "x" * (256 * 1024)})


def test_registry_redacts_results_before_enforcing_the_persisted_limit() -> None:
    registry = JobRegistry()
    registry.register(echo_definition())

    assert registry.validate_result("echo", 1, {"api_key": "raw", "echo": "hello"}) == {
        "api_key": "[REDACTED]",
        "echo": "hello",
    }
    with pytest.raises(JobResultTooLargeError):
        registry.validate_result("echo", 1, {"data": "x" * (64 * 1024)})


@pytest.mark.parametrize(
    "raw",
    [
        {"message": "hi", "api_key": "raw"},
        {"message": "hi", "nested": {"access_token": "raw"}},
        {"message": "hi", "PASSWORD": "raw"},
    ],
)
def test_registry_rejects_raw_secret_fields_before_model_validation(raw) -> None:
    registry = JobRegistry()
    registry.register(echo_definition())

    with pytest.raises(JobSecretMaterialError):
        registry.validate_payload("echo", 1, raw)


def test_registry_rejects_pydantic_secret_values() -> None:
    registry = JobRegistry()
    registry.register(
        echo_definition(
            name="secret_payload",
            payload_model=SecretPayload,
            handler=lambda c, p: None,
        )
    )

    with pytest.raises(JobSecretMaterialError):
        registry.validate_payload(
            "secret_payload", 1, {"credential": SecretStr("raw-secret")}
        )


def test_manual_definitions_respect_role_hierarchy_and_scope() -> None:
    registry = JobRegistry()
    registry.register(echo_definition(name="admin-only", minimum_manual_role="admin"))
    registry.register(
        echo_definition(name="contributors", minimum_manual_role="contributor")
    )
    registry.register(
        echo_definition(
            name="system-only",
            allowed_scopes=frozenset({"system"}),
            minimum_manual_role="admin",
        )
    )

    contributor_names = [
        item.name for item in registry.manual_definitions(minimum_role="contributor")
    ]
    admin_names = [
        item.name for item in registry.manual_definitions(minimum_role="admin")
    ]
    assert contributor_names == ["contributors"]
    assert admin_names == [
        "admin-only",
        "contributors",
    ]
