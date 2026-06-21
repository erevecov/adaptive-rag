"""Contrato conversacional compartido para M5."""

from adaptive_rag.chat.audit import (
    ChatAuditWriter,
    InMemoryChatAuditWriter,
    NullChatAuditWriter,
)
from adaptive_rag.chat.errors import ChatServiceError
from adaptive_rag.chat.models import (
    ChatRequest,
    ChatResponse,
    ChatRunnerOutput,
    ChatRunnerRequest,
    ChatToolCall,
)
from adaptive_rag.chat.qwen import QwenChatRunner, QwenChatRunnerError
from adaptive_rag.chat.runners import RetrievalGroundedChatRunner
from adaptive_rag.chat.service import ChatRunner, ChatService

__all__ = [
    "ChatAuditWriter",
    "ChatRequest",
    "ChatResponse",
    "ChatRunner",
    "ChatRunnerOutput",
    "ChatRunnerRequest",
    "ChatService",
    "ChatServiceError",
    "ChatToolCall",
    "InMemoryChatAuditWriter",
    "NullChatAuditWriter",
    "QwenChatRunner",
    "QwenChatRunnerError",
    "RetrievalGroundedChatRunner",
]
