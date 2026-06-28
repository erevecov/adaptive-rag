"""Tests for opt-in local Okapi BM25 retrieval."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Chunk, Document, DocumentVersion, Project, Source
from adaptive_rag.db.repositories import (
    ChunkRepository,
    DocumentRepository,
    ProjectRepository,
    SourceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.retrieval import DenseRetrievalFilters
from adaptive_rag.retrieval.bm25 import Bm25RetrievalError, Bm25Retriever


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


def _create_project(session, name: str) -> Project:
    return ProjectRepository(session).create(name=name)


def _create_chunk(
    session,
    *,
    project: Project,
    source_type: str = "markdown",
    external_id: str,
    tags: tuple[str, ...] = (),
    stable_id: str,
    text: str,
    snippet: str,
    contextual_summary: str | None = None,
    source_created_at: datetime | None = None,
    document_created_at: datetime | None = None,
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
    )
    if source_created_at is not None:
        source.created_at = source_created_at
    if document_created_at is not None:
        document.created_at = document_created_at
    session.flush()
    return source, document, version, chunk


def test_bm25_retriever_prefers_concise_matches_over_long_matches() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    filler = " ".join(f"filler{i}" for i in range(80))
    _long_source, _long_document, _long_version, long_match = _create_chunk(
        session,
        project=project,
        external_id="long.md",
        stable_id="long",
        text=f"SKU 42 manual {filler}",
        snippet=f"SKU 42 manual {filler}",
    )
    source, document, version, short_match = _create_chunk(
        session,
        project=project,
        external_id="short.md",
        tags=("docs",),
        stable_id="short",
        text="Header\n\nSKU 42 manual",
        snippet="SKU 42 manual",
    )
    session.commit()

    results = Bm25Retriever(session).search(
        project_id=project.id,
        query="SKU 42 manual",
        limit=2,
    )

    assert [result.chunk_id for result in results] == [short_match.id, long_match.id]
    assert results[0].score > results[1].score
    assert results[0].bm25_metadata == {
        "bm25_rank": 1,
        "bm25_score": results[0].score,
        "used_bm25": True,
    }
    assert results[0].citation.source_id == source.id
    assert results[0].citation.document_id == document.id
    assert results[0].citation.document_version_id == version.id
    assert results[0].citation.snippet == "SKU 42 manual"


def test_bm25_retriever_filters_before_scoring() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    other_project = _create_project(session, "other")
    feb_1 = datetime(2026, 2, 1, tzinfo=UTC)
    feb_2 = datetime(2026, 2, 2, tzinfo=UTC)
    wanted_source, wanted_document, _version, wanted = _create_chunk(
        session,
        project=project,
        external_id="wanted.md",
        tags=("docs", "v1"),
        stable_id="wanted",
        text="Invoice ID 777 belongs to the wanted source.",
        snippet="Invoice ID 777 belongs to the wanted source.",
        source_created_at=feb_1,
        document_created_at=feb_2,
    )
    _create_chunk(
        session,
        project=project,
        source_type="text",
        external_id="wrong-type.txt",
        tags=("docs", "v1"),
        stable_id="wrong-type",
        text="Invoice ID 777 belongs to the wrong source type.",
        snippet="Invoice ID 777 belongs to the wrong source type.",
        source_created_at=feb_1,
        document_created_at=feb_2,
    )
    _create_chunk(
        session,
        project=other_project,
        external_id="other.md",
        tags=("docs", "v1"),
        stable_id="other",
        text="Invoice ID 777 belongs to another project.",
        snippet="Invoice ID 777 belongs to another project.",
        source_created_at=feb_1,
        document_created_at=feb_2,
    )
    session.commit()

    results = Bm25Retriever(session).search(
        project_id=project.id,
        query="invoice 777",
        limit=5,
        filters=DenseRetrievalFilters(
            source_id=wanted_source.id,
            document_id=wanted_document.id,
            source_type="markdown",
            tags=("docs", "v1"),
            source_created_at_from=datetime(2026, 1, 31, tzinfo=UTC),
            source_created_at_to=datetime(2026, 2, 3, tzinfo=UTC),
            document_created_at_from=datetime(2026, 2, 1, tzinfo=UTC),
            document_created_at_to=datetime(2026, 2, 3, tzinfo=UTC),
        ),
    )

    assert [result.chunk_id for result in results] == [wanted.id]


def test_bm25_retriever_rejects_invalid_request() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    session.commit()

    with pytest.raises(Bm25RetrievalError, match="limit must be positive"):
        Bm25Retriever(session).search(
            project_id=project.id,
            query="invoice",
            limit=0,
        )
