"""Tests for sparse embedding backfill pipeline."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Chunk,
    ChunkSparseEmbedding,
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
from adaptive_rag.embeddings import (
    FakeSparseEmbeddingProvider,
    SparseEmbeddingPipeline,
    SparseEmbeddingPipelineError,
)


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Workspace.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
            ChunkSparseEmbedding.__table__,
        ],
    )
    return create_session_factory(engine)()


def _create_document_version(
    session, *, text: str
) -> tuple[Workspace, DocumentVersion]:
    workspace = WorkspaceRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        workspace_id=workspace.id,
        source_type="markdown",
        external_id="guide.md",
    )
    document = DocumentRepository(session).create_document(
        workspace_id=workspace.id,
        source_id=source.id,
        stable_id="guide.md",
    )
    version = DocumentRepository(session).create_version(
        workspace_id=workspace.id,
        document_id=document.id,
        version_number=1,
        normalized_text=text,
        content_hash="sha256:test",
        index_fingerprint="ingestion-fp",
    )
    session.flush()
    return workspace, version


def _create_chunks(
    session,
    *,
    workspace: Workspace,
    version: DocumentVersion,
) -> list[Chunk]:
    text = version.normalized_text
    first_start = text.index("Alpha")
    first_end = text.index("\n\n## Details")
    second_start = text.index("Delta")
    repo = ChunkRepository(session)
    first = repo.create(
        workspace_id=workspace.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=first_start,
        char_end=first_end,
        token_count=6,
        contextual_summary="Generated context for Alpha.",
    )
    second = repo.create(
        workspace_id=workspace.id,
        document_version_id=version.id,
        ordinal=1,
        char_start=second_start,
        char_end=len(text),
        token_count=5,
    )
    session.flush()
    return [first, second]


def test_sparse_embedding_pipeline_backfills_contextualized_inputs_idempotently() -> (
    None
):
    text = (
        "# Product Guide\n\n"
        "## Intro\n\n"
        "Alpha beta evidence explains onboarding for local users.\n\n"
        "## Details\n\n"
        "Delta evidence covers cited answers."
    )
    session = _make_session()
    workspace, version = _create_document_version(session, text=text)
    chunks = _create_chunks(session, workspace=workspace, version=version)
    provider = FakeSparseEmbeddingProvider()

    first = SparseEmbeddingPipeline(session, provider=provider).embed_document_version(
        workspace_id=workspace.id,
        document_version_id=version.id,
    )
    second = SparseEmbeddingPipeline(session, provider=provider).embed_document_version(
        workspace_id=workspace.id,
        document_version_id=version.id,
    )
    session.commit()

    rows = session.scalars(
        select(ChunkSparseEmbedding).order_by(ChunkSparseEmbedding.created_at)
    ).all()
    first_chunk_text = text[chunks[0].char_start : chunks[0].char_end]

    assert first.embedded_chunk_count == 2
    assert first.reused_chunk_count == 0
    assert second.embedded_chunk_count == 0
    assert second.reused_chunk_count == 2
    assert len(rows) == 2
    assert provider.document_inputs == [
        f"Generated context for Alpha.\n\n{first_chunk_text}",
        text[chunks[1].char_start : chunks[1].char_end],
    ]
    assert rows[0].input_hash.startswith("sha256:")
    assert rows[0].index_fingerprint.startswith("sha256:")
    assert rows[0].extra_metadata["sparse_metadata_version"] == "sparse_embedding_v1"
    assert rows[0].extra_metadata["sparse_provider"] == "fake"
    assert rows[0].extra_metadata["sparse_model"] == "fake-sparse-embedding-v1"
    assert rows[0].extra_metadata["sparse_input_kind"] == (
        "contextual_summary_plus_chunk_text"
    )


def test_sparse_embedding_pipeline_rejects_cross_workspace_version() -> None:
    session = _make_session()
    workspace, version = _create_document_version(session, text="Alpha evidence")
    other_workspace = WorkspaceRepository(session).create(name="other")
    provider = FakeSparseEmbeddingProvider()
    session.commit()

    with pytest.raises(
        SparseEmbeddingPipelineError,
        match="document version does not belong to workspace",
    ):
        SparseEmbeddingPipeline(session, provider=provider).embed_document_version(
            workspace_id=other_workspace.id,
            document_version_id=version.id,
        )

    assert workspace.id != other_workspace.id
    assert session.scalar(select(func.count()).select_from(ChunkSparseEmbedding)) == 0
