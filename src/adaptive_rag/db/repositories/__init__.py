"""Repositories publicos para persistencia del dominio Adaptive RAG."""

from adaptive_rag.db.repositories.chat_attachments import ChatAttachmentRepository
from adaptive_rag.db.repositories.chat_audit import (
    ChatAuditRepository,
    ChatSessionDetail,
    ChatSessionSummary,
    ChatSessionSummaryPage,
    ProviderUsageRepository,
)
from adaptive_rag.db.repositories.chat_observability import (
    ChatObservabilityErrorMessage,
    ChatObservabilityErrorSummary,
    ChatObservabilityFilters,
    ChatObservabilityLatencySummary,
    ChatObservabilityProviderUsageGroup,
    ChatObservabilityProviderUsageSummary,
    ChatObservabilityRepository,
    ChatObservabilitySessionSummary,
    ChatObservabilitySummary,
)
from adaptive_rag.db.repositories.chunks import ChunkRepository
from adaptive_rag.db.repositories.documents import DocumentRepository
from adaptive_rag.db.repositories.filters import DocumentFilters, SourceFilters
from adaptive_rag.db.repositories.graph_projection import GraphprojectionRepository
from adaptive_rag.db.repositories.job_runtime import JobRuntimeRepository
from adaptive_rag.db.repositories.jobs import JobRepository
from adaptive_rag.db.repositories.knowledge_proposals import KnowledgeProposalRepository
from adaptive_rag.db.repositories.provider_connections import (
    ProviderConnectionRepository,
    ProviderModelCatalogRepository,
    ProviderSecretStatus,
)
from adaptive_rag.db.repositories.runtime_settings import (
    ChatRetrievalSettingsRepository,
    EffectiveChatModel,
    EffectiveChatRetrievalSettings,
    EffectiveRuntimeSlot,
    RuntimeSettingsRepository,
    WorkspaceRuntimeSettings,
    WorkspaceRuntimeSettingsRepository,
)
from adaptive_rag.db.repositories.sources import SourceRepository
from adaptive_rag.db.repositories.sparse_embeddings import SparseEmbeddingRepository
from adaptive_rag.db.repositories.system_tasks import SystemTaskRepository
from adaptive_rag.db.repositories.user_memories import UserMemoryRepository
from adaptive_rag.db.repositories.users import (
    HumanAuthRepository,
    UserRepository,
    WorkspaceMembershipRepository,
)
from adaptive_rag.db.repositories.workspaces import WorkspaceRepository

__all__ = [
    "ChatAttachmentRepository",
    "ChatAuditRepository",
    "ChatObservabilityErrorMessage",
    "ChatObservabilityErrorSummary",
    "ChatObservabilityFilters",
    "ChatObservabilityLatencySummary",
    "ChatObservabilityProviderUsageGroup",
    "ChatObservabilityProviderUsageSummary",
    "ChatObservabilityRepository",
    "ChatRetrievalSettingsRepository",
    "ChatObservabilitySessionSummary",
    "ChatObservabilitySummary",
    "ChatSessionDetail",
    "ChatSessionSummary",
    "ChatSessionSummaryPage",
    "ChunkRepository",
    "DocumentFilters",
    "DocumentRepository",
    "GraphprojectionRepository",
    "JobRepository",
    "JobRuntimeRepository",
    "KnowledgeProposalRepository",
    "WorkspaceMembershipRepository",
    "WorkspaceRepository",
    "ProviderConnectionRepository",
    "ProviderModelCatalogRepository",
    "ProviderSecretStatus",
    "ProviderUsageRepository",
    "EffectiveChatRetrievalSettings",
    "EffectiveChatModel",
    "EffectiveRuntimeSlot",
    "WorkspaceRuntimeSettings",
    "WorkspaceRuntimeSettingsRepository",
    "RuntimeSettingsRepository",
    "SourceFilters",
    "SourceRepository",
    "SparseEmbeddingRepository",
    "SystemTaskRepository",
    "UserRepository",
    "HumanAuthRepository",
    "UserMemoryRepository",
]
