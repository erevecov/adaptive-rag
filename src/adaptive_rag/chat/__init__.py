"""Contrato conversacional compartido para M5."""

from adaptive_rag.chat.audit import (
    ChatAuditWriter,
    InMemoryChatAuditWriter,
    NullChatAuditWriter,
    SqlAlchemyChatAuditWriter,
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
from adaptive_rag.chat.streaming import (
    ChatStep,
    ChatStepUsage,
    ChatStreamEvent,
    ChatStreamEventName,
    chat_stream_answer_delta_event,
    chat_stream_error_event,
    chat_stream_final_event,
    chat_stream_heartbeat_event,
    chat_stream_session_started_event,
    chat_stream_step_event,
    chat_stream_tool_call_event,
    serialize_chat_step,
    serialize_chat_stream_event,
)

__all__ = [
    "ChatAuditWriter",
    "ChatRequest",
    "ChatResponse",
    "ChatRunner",
    "ChatRunnerOutput",
    "ChatRunnerRequest",
    "ChatService",
    "ChatServiceError",
    "ChatStep",
    "ChatStepUsage",
    "ChatStreamEvent",
    "ChatStreamEventName",
    "ChatToolCall",
    "InMemoryChatAuditWriter",
    "NullChatAuditWriter",
    "QwenChatRunner",
    "QwenChatRunnerError",
    "RetrievalGroundedChatRunner",
    "SqlAlchemyChatAuditWriter",
    "chat_stream_answer_delta_event",
    "chat_stream_error_event",
    "chat_stream_final_event",
    "chat_stream_heartbeat_event",
    "chat_stream_session_started_event",
    "chat_stream_step_event",
    "chat_stream_tool_call_event",
    "serialize_chat_stream_event",
    "serialize_chat_step",
]
