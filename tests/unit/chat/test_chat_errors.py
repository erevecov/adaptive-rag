"""Tests for structured chat error classification."""

from __future__ import annotations

from adaptive_rag.chat.errors import ChatServiceError, classify_chat_error


def test_chat_service_error_payload_is_structured() -> None:
    exc = ChatServiceError(
        "session is archived",
        code="session_archived",
        retryable=False,
        status_code=422,
    )

    assert exc.to_payload().as_dict() == {
        "code": "session_archived",
        "detail": "session is archived",
        "message": "session is archived",
        "retryable": False,
    }


def test_classify_maps_rate_limit_and_timeout() -> None:
    rate = classify_chat_error(RuntimeError("HTTP 429 rate limit exceeded"))
    assert rate.code == "provider_rate_limited"
    assert rate.retryable is True
    assert "429" in rate.message

    timeout = classify_chat_error(TimeoutError("request timeout after 30s"))
    assert timeout.code == "provider_timeout"
    assert timeout.retryable is True


def test_classify_preserves_chat_service_error_fields() -> None:
    payload = classify_chat_error(
        ChatServiceError(
            "client_disconnected",
            code="client_disconnected",
            retryable=False,
        )
    )
    assert payload.code == "client_disconnected"
    assert payload.message == "client_disconnected"
    assert payload.retryable is False
