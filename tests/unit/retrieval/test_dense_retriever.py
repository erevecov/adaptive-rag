"""Tests del dense retrieval baseline."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    EMBEDDING_DIMENSIONS,
    Chunk,
    Document,
    DocumentVersion,
    Project,
    Source,
)
from adaptive_rag.db.repositories import (
    ChunkRepository,
    DocumentRepository,
    ProjectRepository,
    SourceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.retrieval import (
    DenseRetrievalError,
    DenseRetrievalFilters,
    DenseRetriever,
)


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


def _vector(first: float, second: float = 0.0) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = first
    values[1] = second
    return values


def _create_project(session, name: str) -> Project:
    return ProjectRepository(session).create(name=name)


def _create_embedded_chunk(
    session,
    *,
    project: Project,
    source_type: str = "markdown",
    external_id: str,
    tags: tuple[str, ...] = (),
    stable_id: str,
    text: str,
    snippet: str,
    embedding: list[float] | None,
    source_created_at: datetime | None = None,
    document_created_at: datetime | None = None,
    contextual_summary: str | None = None,
) -> tuple[Source, Document, DocumentVersion, Chunk]:
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type=source_type,
        external_id=external_id,
        tags=tags,
        extra_metadata={"title": external_id},
    )
    document = DocumentRepository(session).create_document(
        project_id=project.id,
        source_id=source.id,
        stable_id=stable_id,
    )
    version = DocumentRepository(session).create_version(
        project_id=project.id,
        document_id=document.id,
        version_number=1,
        normalized_text=text,
        content_hash=f"sha256:{stable_id}",
        index_fingerprint=f"fp:{stable_id}",
    )
    char_start = text.index(snippet)
    chunk = ChunkRepository(session).create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=char_start,
        char_end=char_start + len(snippet),
        token_count=3,
        section_metadata={"heading": stable_id, "section_path": [stable_id]},
        chunker_metadata={"chunker_version": "semantic_markdown_v1"},
        contextual_summary=contextual_summary,
        embedding=embedding,
    )
    if source_created_at is not None:
        source.created_at = source_created_at
    if document_created_at is not None:
        document.created_at = document_created_at
    session.flush()
    return source, document, version, chunk


def test_dense_retriever_ranks_by_l2_and_returns_original_citation() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    _source_far, _document_far, _version_far, far = _create_embedded_chunk(
        session,
        project=project,
        external_id="far.md",
        tags=("docs",),
        stable_id="far",
        text="Far original text",
        snippet="Far original text",
        embedding=_vector(0.9),
    )
    source_near, document_near, version_near, near = _create_embedded_chunk(
        session,
        project=project,
        external_id="near.md",
        tags=("docs", "v1"),
        stable_id="near",
        text="Header\n\nAlpha original evidence",
        snippet="Alpha original evidence",
        embedding=_vector(0.1),
        contextual_summary="Generated context must not become the citation.",
    )
    session.commit()

    results = DenseRetriever(session).search(
        project_id=project.id,
        query_embedding=_vector(0.0),
        limit=2,
    )

    assert [result.chunk_id for result in results] == [near.id, far.id]
    assert results[0].distance == pytest.approx(0.1)
    assert results[0].score == pytest.approx(1 / 1.1)
    assert results[0].citation.source_id == source_near.id
    assert results[0].citation.source_external_id == "near.md"
    assert results[0].citation.source_tags == ("docs", "v1")
    assert results[0].citation.document_id == document_near.id
    assert results[0].citation.document_version_id == version_near.id
    assert results[0].citation.snippet == "Alpha original evidence"
    assert "Generated context" not in results[0].citation.snippet
    assert results[0].citation.section_metadata == {
        "heading": "near",
        "section_path": ["near"],
    }


def test_dense_retriever_filters_project_before_ranking() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    other_project = _create_project(session, "other")
    _source_a, _document_a, _version_a, project_chunk = _create_embedded_chunk(
        session,
        project=project,
        external_id="project.md",
        stable_id="project-doc",
        text="Project evidence",
        snippet="Project evidence",
        embedding=_vector(0.8),
    )
    _create_embedded_chunk(
        session,
        project=other_project,
        external_id="other.md",
        stable_id="other-doc",
        text="Other project evidence",
        snippet="Other project evidence",
        embedding=_vector(0.0),
    )
    session.commit()

    results = DenseRetriever(session).search(
        project_id=project.id,
        query_embedding=_vector(0.0),
        limit=5,
    )

    assert [result.chunk_id for result in results] == [project_chunk.id]


def test_dense_retriever_applies_filters_before_ranking() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    feb_1 = datetime(2026, 2, 1, tzinfo=UTC)
    feb_2 = datetime(2026, 2, 2, tzinfo=UTC)
    wanted_source, wanted_document, _version, wanted_chunk = _create_embedded_chunk(
        session,
        project=project,
        external_id="wanted.md",
        tags=("docs", "v1"),
        stable_id="wanted-doc",
        text="Wanted evidence",
        snippet="Wanted evidence",
        embedding=_vector(0.4),
        source_created_at=feb_1,
        document_created_at=feb_2,
    )
    _create_embedded_chunk(
        session,
        project=project,
        external_id="same-source-other-doc.md",
        tags=("docs", "v1"),
        stable_id="same-source-other-doc",
        text="Other document evidence",
        snippet="Other document evidence",
        embedding=_vector(0.0),
        source_created_at=feb_1,
        document_created_at=feb_2,
    )
    _create_embedded_chunk(
        session,
        project=project,
        external_id="wrong-tag.md",
        tags=("blog",),
        stable_id="wrong-tag-doc",
        text="Wrong tag evidence",
        snippet="Wrong tag evidence",
        embedding=_vector(0.0),
        source_created_at=feb_1,
        document_created_at=feb_2,
    )
    _create_embedded_chunk(
        session,
        project=project,
        source_type="text",
        external_id="wrong-type.txt",
        tags=("docs", "v1"),
        stable_id="wrong-type-doc",
        text="Wrong type evidence",
        snippet="Wrong type evidence",
        embedding=_vector(0.0),
        source_created_at=feb_1,
        document_created_at=feb_2,
    )
    session.commit()

    tag_and_type_results = DenseRetriever(session).search(
        project_id=project.id,
        query_embedding=_vector(0.0),
        limit=5,
        filters=DenseRetrievalFilters(source_type="markdown", tags=("docs", "v1")),
    )
    document_results = DenseRetriever(session).search(
        project_id=project.id,
        query_embedding=_vector(0.0),
        limit=5,
        filters=DenseRetrievalFilters(
            source_id=wanted_source.id,
            document_id=wanted_document.id,
            source_created_at_from=datetime(2026, 1, 31, tzinfo=UTC),
            source_created_at_to=datetime(2026, 2, 3, tzinfo=UTC),
            document_created_at_from=datetime(2026, 2, 1, tzinfo=UTC),
            document_created_at_to=datetime(2026, 2, 3, tzinfo=UTC),
        ),
    )

    assert {result.citation.source_external_id for result in tag_and_type_results} == {
        "same-source-other-doc.md",
        "wanted.md",
    }
    assert [result.chunk_id for result in document_results] == [wanted_chunk.id]


def test_dense_retriever_ignores_chunks_without_embeddings() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    _create_embedded_chunk(
        session,
        project=project,
        external_id="missing.md",
        stable_id="missing-doc",
        text="Missing embedding evidence",
        snippet="Missing embedding evidence",
        embedding=None,
    )
    session.commit()

    results = DenseRetriever(session).search(
        project_id=project.id,
        query_embedding=_vector(0.0),
    )

    assert results == []


def test_dense_retriever_rejects_invalid_inputs() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    session.commit()

    with pytest.raises(DenseRetrievalError, match="query embedding dimension mismatch"):
        DenseRetriever(session).search(project_id=project.id, query_embedding=[0.0])

    with pytest.raises(DenseRetrievalError, match="limit must be positive"):
        DenseRetriever(session).search(
            project_id=project.id,
            query_embedding=_vector(0.0),
            limit=0,
        )
