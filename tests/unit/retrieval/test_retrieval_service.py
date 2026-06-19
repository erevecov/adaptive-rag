"""Tests del contrato compartido de retrieval M4."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

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
    RetrievalMetadataFilter,
    RetrievalSearchRequest,
    RetrievalService,
    RetrievalServiceError,
)

PROJECT_ID = uuid4()


class StaticQueryEmbeddingProvider:
    provider_name = "fake"
    model_name = "static-query-v1"
    dimensions = EMBEDDING_DIMENSIONS

    def __init__(self, embedding: list[float]) -> None:
        self.embedding = embedding
        self.inputs: list[str] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.inputs.extend(texts)
        return [list(self.embedding) for _text in texts]


class WrongDimensionQueryEmbeddingProvider:
    provider_name = "fake"
    model_name = "wrong-query-dimension-v1"
    dimensions = EMBEDDING_DIMENSIONS

    def __init__(self) -> None:
        self.inputs: list[str] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.inputs.extend(texts)
        return [[0.1, 0.2, 0.3] for _text in texts]


def _make_session() -> Session:
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


def _create_project(session: Session, name: str) -> Project:
    return ProjectRepository(session).create(name=name)


def _create_embedded_chunk(
    session: Session,
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
        embedding=embedding,
    )
    if source_created_at is not None:
        source.created_at = source_created_at
    if document_created_at is not None:
        document.created_at = document_created_at
    session.flush()
    return source, document, version, chunk


def test_retrieval_service_embeds_query_and_returns_dense_results() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    _far_source, _far_document, _far_version, far = _create_embedded_chunk(
        session,
        project=project,
        external_id="far.md",
        stable_id="far",
        text="Far original text",
        snippet="Far original text",
        embedding=_vector(0.9),
    )
    _near_source, _near_document, _near_version, near = _create_embedded_chunk(
        session,
        project=project,
        external_id="near.md",
        stable_id="near",
        text="Header\n\nAlpha original evidence",
        snippet="Alpha original evidence",
        embedding=_vector(0.1),
    )
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    session.commit()

    results = RetrievalService(session, provider=provider).search(
        RetrievalSearchRequest(project_id=project.id, query="alpha question", limit=2)
    )

    assert provider.inputs == ["alpha question"]
    assert [result.chunk_id for result in results] == [near.id, far.id]
    assert results[0].distance == pytest.approx(0.1)
    assert results[0].score == pytest.approx(1 / 1.1)
    assert results[0].citation.snippet == "Alpha original evidence"


def test_retrieval_service_maps_metadata_filter_to_dense_filters() -> None:
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
        external_id="wrong-doc.md",
        tags=("docs", "v1"),
        stable_id="wrong-doc",
        text="Wrong document evidence",
        snippet="Wrong document evidence",
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
        stable_id="wrong-type",
        text="Wrong type evidence",
        snippet="Wrong type evidence",
        embedding=_vector(0.0),
        source_created_at=feb_1,
        document_created_at=feb_2,
    )
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    session.commit()

    results = RetrievalService(session, provider=provider).search(
        RetrievalSearchRequest(
            project_id=project.id,
            query="filtered question",
            limit=5,
            metadata_filter=RetrievalMetadataFilter(
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
    )

    assert provider.inputs == ["filtered question"]
    assert [result.chunk_id for result in results] == [wanted_chunk.id]


@pytest.mark.parametrize(
    ("search_request", "message"),
    [
        (
            RetrievalSearchRequest(project_id=PROJECT_ID, query=" "),
            "query must not be empty",
        ),
        (
            RetrievalSearchRequest(project_id=PROJECT_ID, query="x", limit=0),
            "limit must be positive",
        ),
        (
            RetrievalSearchRequest(
                project_id=PROJECT_ID,
                query="x",
                metadata_filter=RetrievalMetadataFilter(source_type=" "),
            ),
            "source_type must not be empty",
        ),
        (
            RetrievalSearchRequest(
                project_id=PROJECT_ID,
                query="x",
                metadata_filter=RetrievalMetadataFilter(tags=("",)),
            ),
            "tags must not be empty",
        ),
        (
            RetrievalSearchRequest(
                project_id=PROJECT_ID,
                query="x",
                metadata_filter=RetrievalMetadataFilter(
                    source_created_at_from=datetime(2026, 2, 2, tzinfo=UTC),
                    source_created_at_to=datetime(2026, 2, 1, tzinfo=UTC),
                ),
            ),
            "source_created_at range is invalid",
        ),
    ],
)
def test_retrieval_service_rejects_invalid_requests_without_provider_call(
    search_request: RetrievalSearchRequest,
    message: str,
) -> None:
    session = _make_session()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))

    with pytest.raises(RetrievalServiceError, match=message):
        RetrievalService(session, provider=provider).search(search_request)

    assert provider.inputs == []


def test_retrieval_service_rejects_wrong_query_embedding_dimension() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    provider = WrongDimensionQueryEmbeddingProvider()
    session.commit()

    with pytest.raises(
        RetrievalServiceError,
        match="query embedding dimension mismatch",
    ):
        RetrievalService(session, provider=provider).search(
            RetrievalSearchRequest(
                project_id=project.id,
                query="dimension question",
            )
        )

    assert provider.inputs == ["dimension question"]
