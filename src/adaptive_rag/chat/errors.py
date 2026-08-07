"""Errores estables de la capa conversacional."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChatErrorPayload:
    """Contrato estable de error para HTTP 4xx y eventos SSE."""

    code: str
    message: str
    retryable: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            # detail mirrors message for older clients that only read detail.
            "detail": self.message,
        }


class ChatServiceError(ValueError):
    """Error de chat/tool calling con contrato estructurado."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "chat_error",
        retryable: bool = False,
        status_code: int = 422,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable
        self.status_code = status_code

    def to_payload(self) -> ChatErrorPayload:
        return ChatErrorPayload(
            code=self.code,
            message=self.message,
            retryable=self.retryable,
        )


def classify_chat_error(exc: BaseException) -> ChatErrorPayload:
    """Map provider/runtime exceptions to short, actionable operator messages."""

    if isinstance(exc, ChatServiceError):
        return exc.to_payload()

    text = str(exc).strip() or type(exc).__name__
    lowered = text.lower()
    if "429" in text or "rate limit" in lowered or "too many requests" in lowered:
        return ChatErrorPayload(
            code="provider_rate_limited",
            message=(
                "Chat provider rate-limited the request (HTTP 429). "
                "Wait a moment and use Try again."
            ),
            retryable=True,
        )
    if "timeout" in lowered:
        return ChatErrorPayload(
            code="provider_timeout",
            message="Chat provider timed out. Use Try again, or lower retrieval limit.",
            retryable=True,
        )
    if "status 5" in lowered:
        return ChatErrorPayload(
            code="provider_server_error",
            message="Chat provider returned a temporary server error. Use Try again.",
            retryable=True,
        )
    if text == "client_disconnected":
        return ChatErrorPayload(
            code="client_disconnected",
            message="client_disconnected",
            retryable=False,
        )
    if "session" in lowered and "archiv" in lowered:
        return ChatErrorPayload(
            code="session_archived",
            message=text if len(text) <= 280 else text[:277] + "...",
            retryable=False,
        )
    if len(text) > 280:
        text = text[:277] + "..."
    return ChatErrorPayload(
        code="chat_error",
        message=text,
        retryable=False,
    )
