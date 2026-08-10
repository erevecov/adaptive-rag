"""Modelos SQLAlchemy del dominio Adaptive RAG."""

from adaptive_rag.db.models.chat_attachment import (
    CHAT_ATTACHMENT_KIND_VALUES,
    CHAT_ATTACHMENT_STATUS_VALUES,
    ChatAttachment,
)
from adaptive_rag.db.models.chat_message import CHAT_MESSAGE_ROLE_VALUES, ChatMessage
from adaptive_rag.db.models.chat_session import CHAT_SESSION_STATUS_VALUES, ChatSession
from adaptive_rag.db.models.chunk import EMBEDDING_DIMENSIONS, Chunk
from adaptive_rag.db.models.chunk_sparse_embedding import ChunkSparseEmbedding
from adaptive_rag.db.models.document import Document
from adaptive_rag.db.models.document_version import DocumentVersion
from adaptive_rag.db.models.graph_projection import (
    GRAPH_projection_BACKEND_VALUES,
    GRAPH_projection_STATUS_VALUES,
    Graphprojection,
)
from adaptive_rag.db.models.job import JOB_STATUS_VALUES, Job
from adaptive_rag.db.models.job_event import JOB_EVENT_TYPE_VALUES, JobEvent
from adaptive_rag.db.models.knowledge_proposal import (
    KNOWLEDGE_PROPOSAL_STATUS_VALUES,
    KnowledgeProposal,
)
from adaptive_rag.db.models.provider_connection import (
    PROVIDER_CONNECTION_CAPABILITY_VALUES,
    PROVIDER_CONNECTION_PROVIDER_VALUES,
    PROVIDER_CONNECTION_TYPE_VALUES,
    PROVIDER_SECRET_NAME_VALUES,
    ProviderConnection,
    ProviderModelCatalog,
    ProviderSecret,
)
from adaptive_rag.db.models.provider_usage import (
    PROVIDER_USAGE_OPERATION_VALUES,
    PROVIDER_USAGE_SOURCE_VALUES,
    PROVIDER_USAGE_STATUS_VALUES,
    ProviderUsage,
)
from adaptive_rag.db.models.retrieval_run import RetrievalRun
from adaptive_rag.db.models.retrieved_chunk import RetrievedChunk
from adaptive_rag.db.models.runtime_settings import (
    CHAT_RETRIEVAL_MAX_LIMIT,
    DEFAULT_CHAT_RERANK_CANDIDATE_LIMIT,
    DEFAULT_CHAT_RERANK_ENABLED,
    DEFAULT_CHAT_RETRIEVAL_LIMIT,
    RUNTIME_SLOT_VALUES,
    GlobalChatModel,
    GlobalChatRetrievalSettings,
    RuntimeSlotDefault,
    WorkspaceChatModel,
    WorkspaceChatRetrievalSettings,
    WorkspaceRuntimeSlotOverride,
)
from adaptive_rag.db.models.source import Source
from adaptive_rag.db.models.system_task import (
    PROVIDER_MODEL_PRICING_SYNC_TASK_ID,
    SystemTaskState,
)
from adaptive_rag.db.models.tool_call import TOOL_CALL_STATUS_VALUES, ToolCall
from adaptive_rag.db.models.user import (
    SYSTEM_ROLE_VALUES,
    WORKSPACE_ROLE_VALUES,
    User,
    UserAccessToken,
    WorkspaceMembership,
)
from adaptive_rag.db.models.user_memory import (
    USER_MEMORY_STATUS_VALUES,
    UserMemory,
)
from adaptive_rag.db.models.workspace import JSONWithJSONB, Workspace

__all__ = [
    "CHAT_ATTACHMENT_KIND_VALUES",
    "CHAT_ATTACHMENT_STATUS_VALUES",
    "CHAT_MESSAGE_ROLE_VALUES",
    "CHAT_SESSION_STATUS_VALUES",
    "EMBEDDING_DIMENSIONS",
    "Chunk",
    "ChunkSparseEmbedding",
    "ChatAttachment",
    "ChatMessage",
    "ChatSession",
    "Document",
    "DocumentVersion",
    "CHAT_RETRIEVAL_MAX_LIMIT",
    "DEFAULT_CHAT_RERANK_CANDIDATE_LIMIT",
    "DEFAULT_CHAT_RERANK_ENABLED",
    "DEFAULT_CHAT_RETRIEVAL_LIMIT",
    "GRAPH_projection_BACKEND_VALUES",
    "GRAPH_projection_STATUS_VALUES",
    "GlobalChatRetrievalSettings",
    "GlobalChatModel",
    "Graphprojection",
    "JOB_EVENT_TYPE_VALUES",
    "JOB_STATUS_VALUES",
    "Job",
    "JobEvent",
    "JSONWithJSONB",
    "KNOWLEDGE_PROPOSAL_STATUS_VALUES",
    "KnowledgeProposal",
    "PROVIDER_USAGE_OPERATION_VALUES",
    "PROVIDER_CONNECTION_CAPABILITY_VALUES",
    "PROVIDER_CONNECTION_PROVIDER_VALUES",
    "PROVIDER_CONNECTION_TYPE_VALUES",
    "PROVIDER_SECRET_NAME_VALUES",
    "PROVIDER_USAGE_SOURCE_VALUES",
    "PROVIDER_USAGE_STATUS_VALUES",
    "WORKSPACE_ROLE_VALUES",
    "Workspace",
    "WorkspaceChatRetrievalSettings",
    "WorkspaceChatModel",
    "WorkspaceMembership",
    "WorkspaceRuntimeSlotOverride",
    "ProviderConnection",
    "ProviderModelCatalog",
    "ProviderSecret",
    "ProviderUsage",
    "RetrievalRun",
    "RetrievedChunk",
    "RUNTIME_SLOT_VALUES",
    "RuntimeSlotDefault",
    "Source",
    "PROVIDER_MODEL_PRICING_SYNC_TASK_ID",
    "SystemTaskState",
    "TOOL_CALL_STATUS_VALUES",
    "ToolCall",
    "SYSTEM_ROLE_VALUES",
    "User",
    "UserMemory",
    "USER_MEMORY_STATUS_VALUES",
    "UserAccessToken",
]
