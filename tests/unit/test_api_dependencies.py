"""Focused tests for optional provider construction in API dependencies."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from adaptive_rag.api import dependencies
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    EMBEDDING_DIMENSIONS,
    Chunk,
    Document,
    DocumentVersion,
    Source,
    Workspace,
)
from adaptive_rag.db.repositories import (
    ChunkRepository,
    DocumentRepository,
    SourceRepository,
    WorkspaceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.embeddings import SparseEmbeddingProvider
from adaptive_rag.provider_runtime import ProviderConfigurationError
from adaptive_rag.provider_usage import InMemoryProviderUsageTracker
from adaptive_rag.rerank import FakeRerankProvider
from adaptive_rag.retrieval import RetrievalSearchRequest


class StaticQueryEmbeddingProvider:
    provider_name = "fake"
    model_name = "static-query-v1"
    dimensions = EMBEDDING_DIMENSIONS

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        values = [0.0] * EMBEDDING_DIMENSIONS
        return [list(values) for _text in texts]


def _session_with_dense_corpus() -> tuple[Session, Workspace]:
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Workspace.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
        ],
    )
    session = create_session_factory(engine)()
    workspace = WorkspaceRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        workspace_id=workspace.id,
        source_type="markdown",
        external_id="alpha.md",
    )
    document = DocumentRepository(session).create_document(
        workspace_id=workspace.id,
        source_id=source.id,
        stable_id="alpha",
    )
    version = DocumentRepository(session).create_version(
        workspace_id=workspace.id,
        document_id=document.id,
        version_number=1,
        normalized_text="Alpha evidence",
        content_hash="sha256:alpha",
        index_fingerprint="fp:alpha",
    )
    ChunkRepository(session).create(
        workspace_id=workspace.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=0,
        char_end=len("Alpha evidence"),
        token_count=2,
        section_metadata={"heading": "alpha", "section_path": ["alpha"]},
        chunker_metadata={"chunker_version": "semantic_markdown_v1"},
        embedding=[0.1] + ([0.0] * (EMBEDDING_DIMENSIONS - 1)),
    )
    session.commit()
    return session, workspace


def test_rerank_provider_factory_degrades_configuration_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_configuration_error() -> FakeRerankProvider:
        raise ProviderConfigurationError("missing_provider_secret")

    monkeypatch.setattr(
        dependencies,
        "get_runtime_rerank_provider",
        raise_configuration_error,
    )

    factory = dependencies.get_rerank_provider_factory(
        usage_tracker=InMemoryProviderUsageTracker()
    )

    assert factory() is None


def test_rerank_provider_factory_preserves_configured_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeRerankProvider()
    monkeypatch.setattr(
        dependencies,
        "get_runtime_rerank_provider",
        lambda: provider,
    )

    factory = dependencies.get_rerank_provider_factory(
        usage_tracker=InMemoryProviderUsageTracker()
    )

    assert factory() is provider


def test_rerank_provider_factory_propagates_unexpected_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_unexpected_error() -> FakeRerankProvider:
        raise RuntimeError("programming error")

    monkeypatch.setattr(
        dependencies,
        "get_runtime_rerank_provider",
        raise_unexpected_error,
    )
    factory = dependencies.get_rerank_provider_factory(
        usage_tracker=InMemoryProviderUsageTracker()
    )

    with pytest.raises(RuntimeError, match="programming error"):
        factory()


def test_lazy_chat_retrieval_searcher_treats_sparse_config_error_as_absent() -> (
    None
):
    session, workspace = _session_with_dense_corpus()

    def boom() -> SparseEmbeddingProvider:
        raise ProviderConfigurationError(
            "ADAPTIVE_RAG_SPARSE_EMBEDDING_MODEL must be set"
        )

    searcher = dependencies.LazyChatRetrievalSearcher(
        session=session,
        provider=StaticQueryEmbeddingProvider(),
        sparse_provider_factory=boom,
        rerank_provider_factory=lambda: None,
        graph_retriever=None,
    )

    results = searcher.search(
        RetrievalSearchRequest(
            workspace_id=workspace.id,
            query="alpha",
            limit=3,
            strategy="dense_sparse",
        )
    )

    assert results
    assert results[0].fallback_reason == "sparse_provider_unavailable"
