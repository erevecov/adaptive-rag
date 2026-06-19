"""Errores estables de la capa conversacional."""

from __future__ import annotations


class ChatServiceError(ValueError):
    """Error no retryable de chat/tool calling."""
