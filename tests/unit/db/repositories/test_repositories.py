"""Tests para repositories de dominio.

Los repositories centralizan lecturas y escrituras iniciales sobre la
`Session` de SQLAlchemy sin tomar ownership del commit. El foco de estos
tests es aislamiento por `project_id`, filtros tipados y orden estable.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Chunk, Document, DocumentVersion, Project, Source
from adaptive_rag.db.repositories import (
    ChunkRepository,
    DocumentFilters,
    DocumentRepository,
    ProjectRepository,
    SourceFilters,
    SourceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
        ],
    )
    return create_session_factory(engine)()


def _create_project(session, name: str = "demo") -> Project:
    return ProjectRepository(session).create(name=name)


def _create_source(session, project: Project, external_id: str = "source-1") -> Source:
    return SourceRepository(session).create(
        project_id=project.id,
        source_type="web",
        external_id=external_id,
    )


def _create_document_version(
    session,
    project: Project,
    stable_id: str = "doc-1",
) -> DocumentVersion:
    source = _create_source(session, project)
    document = DocumentRepository(session).create_document(
        project_id=project.id,
        source_id=source.id,
        stable_id=stable_id,
    )
    return DocumentRepository(session).create_version(
        project_id=project.id,
        document_id=document.id,
        version_number=1,
        normalized_text="abcdefghij",
        content_hash=f"sha256:{stable_id}",
        index_fingerprint="fp-1",
    )


def test_project_repository_create_flushes_without_committing():
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    project_id = project.id

    assert project_id is not None

    session.rollback()
    session.expunge_all()

    assert ProjectRepository(session).get(project_id) is None


def test_project_repository_get_returns_project_or_none():
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    session.commit()

    assert ProjectRepository(session).get(project.id).name == "demo"
    assert ProjectRepository(session).get(uuid4()) is None


def test_source_repository_lists_only_requested_project():
    session = _make_session()
    project_a = _create_project(session, "a")
    project_b = _create_project(session, "b")
    source_a = SourceRepository(session).create(
        project_id=project_a.id,
        source_type="web",
        external_id="same-id",
    )
    SourceRepository(session).create(
        project_id=project_b.id,
        source_type="web",
        external_id="same-id",
    )
    session.commit()

    sources = SourceRepository(session).list(project_id=project_a.id)

    assert [source.id for source in sources] == [source_a.id]


def test_source_repository_applies_typed_filters():
    session = _make_session()
    project = _create_project(session)
    wanted = SourceRepository(session).create(
        project_id=project.id,
        source_type="web",
        external_id="docs",
        tags=["docs", "reference"],
    )
    SourceRepository(session).create(
        project_id=project.id,
        source_type="file",
        external_id="docs-file",
        tags=["docs"],
    )
    SourceRepository(session).create(
        project_id=project.id,
        source_type="web",
        external_id="blog",
        tags=["blog"],
    )
    session.commit()

    sources = SourceRepository(session).list(
        project_id=project.id,
        filters=SourceFilters(source_type="web", tag="docs"),
    )

    assert [source.id for source in sources] == [wanted.id]


def test_document_repository_rejects_source_from_different_project():
    session = _make_session()
    project_a = _create_project(session, "a")
    project_b = _create_project(session, "b")
    source_a = _create_source(session, project_a)

    with pytest.raises(ValueError, match="source does not belong to project"):
        DocumentRepository(session).create_document(
            project_id=project_b.id,
            source_id=source_a.id,
            stable_id="cross-project",
        )


def test_document_repository_lists_by_project_and_source():
    session = _make_session()
    project_a = _create_project(session, "a")
    project_b = _create_project(session, "b")
    source_a1 = _create_source(session, project_a, "a1")
    source_a2 = _create_source(session, project_a, "a2")
    source_b = _create_source(session, project_b, "b")
    doc_a1 = DocumentRepository(session).create_document(
        project_id=project_a.id,
        source_id=source_a1.id,
        stable_id="a1-doc",
    )
    DocumentRepository(session).create_document(
        project_id=project_a.id,
        source_id=source_a2.id,
        stable_id="a2-doc",
    )
    DocumentRepository(session).create_document(
        project_id=project_b.id,
        source_id=source_b.id,
        stable_id="b-doc",
    )
    session.commit()

    documents = DocumentRepository(session).list(
        project_id=project_a.id,
        filters=DocumentFilters(source_id=source_a1.id),
    )

    assert [document.id for document in documents] == [doc_a1.id]


def test_document_repository_versions_are_ordered_and_project_scoped():
    session = _make_session()
    project = _create_project(session)
    other_project = _create_project(session, "other")
    source = _create_source(session, project)
    document = DocumentRepository(session).create_document(
        project_id=project.id,
        source_id=source.id,
        stable_id="doc-1",
    )
    DocumentRepository(session).create_version(
        project_id=project.id,
        document_id=document.id,
        version_number=2,
        normalized_text="second",
        content_hash="sha256:2",
        index_fingerprint="fp-2",
    )
    DocumentRepository(session).create_version(
        project_id=project.id,
        document_id=document.id,
        version_number=1,
        normalized_text="first",
        content_hash="sha256:1",
        index_fingerprint="fp-1",
    )
    session.commit()

    versions = DocumentRepository(session).list_versions(
        project_id=project.id,
        document_id=document.id,
    )
    cross_project_versions = DocumentRepository(session).list_versions(
        project_id=other_project.id,
        document_id=document.id,
    )

    assert [version.version_number for version in versions] == [1, 2]
    assert cross_project_versions == []


def test_chunk_repository_lists_by_document_version_ordered_and_project_scoped():
    session = _make_session()
    project = _create_project(session)
    other_project = _create_project(session, "other")
    version = _create_document_version(session, project)
    chunk_repo = ChunkRepository(session)
    chunk_2 = chunk_repo.create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=2,
        char_start=6,
        char_end=10,
    )
    chunk_0 = chunk_repo.create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=0,
        char_end=3,
    )
    chunk_1 = chunk_repo.create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=1,
        char_start=3,
        char_end=6,
    )
    session.commit()

    chunks = chunk_repo.list_by_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    cross_project_chunks = chunk_repo.list_by_document_version(
        project_id=other_project.id,
        document_version_id=version.id,
    )

    assert [chunk.id for chunk in chunks] == [chunk_0.id, chunk_1.id, chunk_2.id]
    assert [chunk.ordinal for chunk in chunks] == [0, 1, 2]
    assert cross_project_chunks == []


def test_chunk_repository_rejects_version_from_different_project():
    session = _make_session()
    project = _create_project(session)
    other_project = _create_project(session, "other")
    version = _create_document_version(session, project)

    with pytest.raises(ValueError, match="document version does not belong to project"):
        ChunkRepository(session).create(
            project_id=other_project.id,
            document_version_id=version.id,
            ordinal=0,
            char_start=0,
            char_end=3,
        )
