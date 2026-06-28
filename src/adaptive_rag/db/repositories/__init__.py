"""Repositories publicos para persistencia del dominio Adaptive RAG."""

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
from adaptive_rag.db.repositories.graph_projection import GraphProjectionRepository
from adaptive_rag.db.repositories.jobs import JobRepository
from adaptive_rag.db.repositories.knowledge_proposals import KnowledgeProposalRepository
from adaptive_rag.db.repositories.projects import ProjectRepository
from adaptive_rag.db.repositories.provider_connections import (
    ProviderConnectionRepository,
    ProviderModelCatalogRepository,
    ProviderSecretStatus,
)
from adaptive_rag.db.repositories.runtime_settings import (
    EffectiveChatModel,
    EffectiveRuntimeSlot,
    ProjectRuntimeSettings,
    ProjectRuntimeSettingsRepository,
    RuntimeSettingsRepository,
)
from adaptive_rag.db.repositories.sources import SourceRepository
from adaptive_rag.db.repositories.sparse_embeddings import SparseEmbeddingRepository
from adaptive_rag.db.repositories.users import (
    ProjectMembershipRepository,
    UserRepository,
)

__all__ = [
    "ChatAuditRepository",
    "ChatObservabilityErrorMessage",
    "ChatObservabilityErrorSummary",
    "ChatObservabilityFilters",
    "ChatObservabilityLatencySummary",
    "ChatObservabilityProviderUsageGroup",
    "ChatObservabilityProviderUsageSummary",
    "ChatObservabilityRepository",
    "ChatObservabilitySessionSummary",
    "ChatObservabilitySummary",
    "ChatSessionDetail",
    "ChatSessionSummary",
    "ChatSessionSummaryPage",
    "ChunkRepository",
    "DocumentFilters",
    "DocumentRepository",
    "GraphProjectionRepository",
    "JobRepository",
    "KnowledgeProposalRepository",
    "ProjectMembershipRepository",
    "ProjectRepository",
    "ProviderConnectionRepository",
    "ProviderModelCatalogRepository",
    "ProviderSecretStatus",
    "ProviderUsageRepository",
    "EffectiveChatModel",
    "EffectiveRuntimeSlot",
    "ProjectRuntimeSettings",
    "ProjectRuntimeSettingsRepository",
    "RuntimeSettingsRepository",
    "SourceFilters",
    "SourceRepository",
    "SparseEmbeddingRepository",
    "UserRepository",
]
