"""Tests para repositories de dominio.

Los repositories centralizan lecturas y escrituras iniciales sobre la
`Session` de SQLAlchemy sin tomar ownership del commit. El foco de estos
tests es aislamiento por `workspace_id`, filtros tipados y orden estable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Chunk, Document, DocumentVersion, Source, Workspace
from adaptive_rag.db.repositories import (
    ChunkRepository,
    DocumentFilters,
    DocumentRepository,
    SourceFilters,
    SourceRepository,
    WorkspaceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


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
        ],
    )
    return create_session_factory(engine)()


def _create_workspace(session, name: str = "demo") -> Workspace:
    return WorkspaceRepository(session).create(name=name)


def _create_source(
    session, workspace: Workspace, external_id: str = "source-1"
) -> Source:
    return SourceRepository(session).create(
        workspace_id=workspace.id,
        source_type="web",
        external_id=external_id,
    )


def _create_document_version(
    session,
    workspace: Workspace,
    stable_id: str = "doc-1",
) -> DocumentVersion:
    source = _create_source(session, workspace)
    document = DocumentRepository(session).create_document(
        workspace_id=workspace.id,
        source_id=source.id,
        stable_id=stable_id,
    )
    return DocumentRepository(session).create_version(
        workspace_id=workspace.id,
        document_id=document.id,
        version_number=1,
        normalized_text="abcdefghij",
        content_hash=f"sha256:{stable_id}",
        index_fingerprint="fp-1",
    )


def test_workspace_repository_create_flushes_without_committing():
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    workspace_id = workspace.id

    assert workspace_id is not None

    session.rollback()
    session.expunge_all()

    assert WorkspaceRepository(session).get(workspace_id) is None


def test_workspace_repository_get_returns_workspace_or_none():
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="demo")
    session.commit()

    assert WorkspaceRepository(session).get(workspace.id).name == "demo"
    assert WorkspaceRepository(session).get(uuid4()) is None


def test_workspace_repository_lists_workspaces_in_deterministic_order():
    session = _make_session()
    newer_b = WorkspaceRepository(session).create(name="b")
    newer_a = WorkspaceRepository(session).create(name="a")
    older = WorkspaceRepository(session).create(name="old")
    same_name_second = WorkspaceRepository(session).create(name="same")
    same_name_first = WorkspaceRepository(session).create(name="same")
    older.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    newer_a.created_at = datetime(2026, 1, 2, tzinfo=UTC)
    newer_b.created_at = datetime(2026, 1, 2, tzinfo=UTC)
    same_name_first.created_at = datetime(2026, 1, 3, tzinfo=UTC)
    same_name_second.created_at = datetime(2026, 1, 3, tzinfo=UTC)
    session.commit()

    workspaces = WorkspaceRepository(session).list()

    assert workspaces == sorted(
        workspaces,
        key=lambda workspace: (workspace.created_at, workspace.name, str(workspace.id)),
    )
    assert [workspace.name for workspace in workspaces[:3]] == ["old", "a", "b"]


def test_source_repository_lists_only_requested_workspace():
    session = _make_session()
    workspace_a = _create_workspace(session, "a")
    workspace_b = _create_workspace(session, "b")
    source_a = SourceRepository(session).create(
        workspace_id=workspace_a.id,
        source_type="web",
        external_id="same-id",
    )
    SourceRepository(session).create(
        workspace_id=workspace_b.id,
        source_type="web",
        external_id="same-id",
    )
    session.commit()

    sources = SourceRepository(session).list(workspace_id=workspace_a.id)

    assert [source.id for source in sources] == [source_a.id]


def test_source_repository_applies_typed_filters():
    session = _make_session()
    workspace = _create_workspace(session)
    wanted = SourceRepository(session).create(
        workspace_id=workspace.id,
        source_type="web",
        external_id="docs",
        tags=["docs", "reference"],
    )
    SourceRepository(session).create(
        workspace_id=workspace.id,
        source_type="file",
        external_id="docs-file",
        tags=["docs"],
    )
    SourceRepository(session).create(
        workspace_id=workspace.id,
        source_type="web",
        external_id="blog",
        tags=["blog"],
    )
    session.commit()

    sources = SourceRepository(session).list(
        workspace_id=workspace.id,
        filters=SourceFilters(source_type="web", tag="docs"),
    )

    assert [source.id for source in sources] == [wanted.id]


def test_document_repository_rejects_source_from_different_workspace():
    session = _make_session()
    workspace_a = _create_workspace(session, "a")
    workspace_b = _create_workspace(session, "b")
    source_a = _create_source(session, workspace_a)

    with pytest.raises(ValueError, match="source does not belong to workspace"):
        DocumentRepository(session).create_document(
            workspace_id=workspace_b.id,
            source_id=source_a.id,
            stable_id="cross-workspace",
        )


def test_document_repository_lists_by_workspace_and_source():
    session = _make_session()
    workspace_a = _create_workspace(session, "a")
    workspace_b = _create_workspace(session, "b")
    source_a1 = _create_source(session, workspace_a, "a1")
    source_a2 = _create_source(session, workspace_a, "a2")
    source_b = _create_source(session, workspace_b, "b")
    doc_a1 = DocumentRepository(session).create_document(
        workspace_id=workspace_a.id,
        source_id=source_a1.id,
        stable_id="a1-doc",
    )
    DocumentRepository(session).create_document(
        workspace_id=workspace_a.id,
        source_id=source_a2.id,
        stable_id="a2-doc",
    )
    DocumentRepository(session).create_document(
        workspace_id=workspace_b.id,
        source_id=source_b.id,
        stable_id="b-doc",
    )
    session.commit()

    documents = DocumentRepository(session).list(
        workspace_id=workspace_a.id,
        filters=DocumentFilters(source_id=source_a1.id),
    )

    assert [document.id for document in documents] == [doc_a1.id]


def test_document_repository_versions_are_ordered_and_workspace_scoped():
    session = _make_session()
    workspace = _create_workspace(session)
    other_workspace = _create_workspace(session, "other")
    source = _create_source(session, workspace)
    document = DocumentRepository(session).create_document(
        workspace_id=workspace.id,
        source_id=source.id,
        stable_id="doc-1",
    )
    DocumentRepository(session).create_version(
        workspace_id=workspace.id,
        document_id=document.id,
        version_number=2,
        normalized_text="second",
        content_hash="sha256:2",
        index_fingerprint="fp-2",
    )
    DocumentRepository(session).create_version(
        workspace_id=workspace.id,
        document_id=document.id,
        version_number=1,
        normalized_text="first",
        content_hash="sha256:1",
        index_fingerprint="fp-1",
    )
    session.commit()

    versions = DocumentRepository(session).list_versions(
        workspace_id=workspace.id,
        document_id=document.id,
    )
    cross_workspace_versions = DocumentRepository(session).list_versions(
        workspace_id=other_workspace.id,
        document_id=document.id,
    )

    assert [version.version_number for version in versions] == [1, 2]
    assert cross_workspace_versions == []


def test_chunk_repository_lists_by_document_version_ordered_and_workspace_scoped():
    session = _make_session()
    workspace = _create_workspace(session)
    other_workspace = _create_workspace(session, "other")
    version = _create_document_version(session, workspace)
    chunk_repo = ChunkRepository(session)
    chunk_2 = chunk_repo.create(
        workspace_id=workspace.id,
        document_version_id=version.id,
        ordinal=2,
        char_start=6,
        char_end=10,
    )
    chunk_0 = chunk_repo.create(
        workspace_id=workspace.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=0,
        char_end=3,
    )
    chunk_1 = chunk_repo.create(
        workspace_id=workspace.id,
        document_version_id=version.id,
        ordinal=1,
        char_start=3,
        char_end=6,
    )
    session.commit()

    chunks = chunk_repo.list_by_document_version(
        workspace_id=workspace.id,
        document_version_id=version.id,
    )
    cross_workspace_chunks = chunk_repo.list_by_document_version(
        workspace_id=other_workspace.id,
        document_version_id=version.id,
    )

    assert [chunk.id for chunk in chunks] == [chunk_0.id, chunk_1.id, chunk_2.id]
    assert [chunk.ordinal for chunk in chunks] == [0, 1, 2]
    assert cross_workspace_chunks == []


def test_chunk_repository_rejects_version_from_different_workspace():
    session = _make_session()
    workspace = _create_workspace(session)
    other_workspace = _create_workspace(session, "other")
    version = _create_document_version(session, workspace)

    with pytest.raises(
        ValueError, match="document version does not belong to workspace"
    ):
        ChunkRepository(session).create(
            workspace_id=other_workspace.id,
            document_version_id=version.id,
            ordinal=0,
            char_start=0,
            char_end=3,
        )


def test_chunk_repository_updates_dense_embedding_workspace_scoped():
    session = _make_session()
    workspace = _create_workspace(session)
    other_workspace = _create_workspace(session, "other")
    version = _create_document_version(session, workspace)
    chunk_repo = ChunkRepository(session)
    chunk = chunk_repo.create(
        workspace_id=workspace.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=0,
        char_end=3,
    )
    metadata = {
        "embedding_dimensions": 1024,
        "embedding_model": "fake-embedding-v1",
    }
    session.commit()

    updated = chunk_repo.update_dense_embedding(
        workspace_id=workspace.id,
        chunk_id=chunk.id,
        embedding=[0.1, 0.2, 0.3],
        embedding_metadata=metadata,
    )

    assert updated.embedding == [0.1, 0.2, 0.3]
    assert updated.embedding_metadata == metadata

    with pytest.raises(ValueError, match="chunk does not belong to workspace"):
        chunk_repo.update_dense_embedding(
            workspace_id=other_workspace.id,
            chunk_id=chunk.id,
            embedding=[0.0],
            embedding_metadata=metadata,
        )
