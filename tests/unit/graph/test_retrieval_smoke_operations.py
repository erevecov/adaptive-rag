from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    EMBEDDING_DIMENSIONS,
    Chunk,
    Document,
    DocumentVersion,
    GraphProjection,
    Project,
    Source,
)
from adaptive_rag.db.repositories import (
    ChunkRepository,
    DocumentRepository,
    ProjectRepository,
    SourceRepository,
)
from adaptive_rag.db.session import create_session_factory
from adaptive_rag.graph import GraphRetrievalResult, GraphStoreUnavailableError
from adaptive_rag.graph.operations import run_graph_retrieval_smoke
from adaptive_rag.retrieval import RetrievalMetadataFilter


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


class RecordingGraphRetriever:
    def __init__(
        self,
        results: tuple[GraphRetrievalResult, ...],
        *,
        failure: Exception | None = None,
    ) -> None:
        self.results = results
        self.failure = failure
        self.requests: list[dict[str, object]] = []

    def expand_project_chunks(
        self,
        *,
        project_id: UUID,
        seed_chunk_ids: tuple[UUID, ...],
        limit: int,
    ) -> tuple[GraphRetrievalResult, ...]:
        self.requests.append(
            {
                "project_id": project_id,
                "seed_chunk_ids": tuple(seed_chunk_ids),
                "limit": limit,
            }
        )
        if self.failure is not None:
            raise self.failure
        return self.results


def test_run_graph_retrieval_smoke_reports_ready_graph_results_with_citations() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    _dense_source, _dense_document, _dense_version, dense_seed = _create_chunk(
        session,
        project=project,
        source_type="markdown",
        external_id="dense.md",
        tags=("docs",),
        stable_id="dense-doc",
        text="Dense seed evidence",
        snippet="Dense seed evidence",
        embedding=_vector(0.1),
    )
    _graph_source, _graph_document, _graph_version, graph_hit = _create_chunk(
        session,
        project=project,
        source_type="markdown",
        external_id="graph.md",
        tags=("docs",),
        stable_id="graph-doc",
        text="Graph expanded evidence",
        snippet="Graph expanded evidence",
        embedding=_vector(0.9),
    )
    _text_source, _text_document, _text_version, text_hit = _create_chunk(
        session,
        project=project,
        source_type="text",
        external_id="filtered.txt",
        tags=("docs",),
        stable_id="filtered-doc",
        text="Filtered graph evidence",
        snippet="Filtered graph evidence",
        embedding=_vector(0.8),
    )
    session.add(GraphProjection(project_id=project.id, status="ready"))
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    graph_retriever = RecordingGraphRetriever(
        (
            GraphRetrievalResult(chunk_id=graph_hit.id, distance=1.0, score=0.5),
            GraphRetrievalResult(chunk_id=text_hit.id, distance=1.0, score=0.5),
        )
    )

    report = run_graph_retrieval_smoke(
        session=session,
        provider=provider,
        graph_retriever=graph_retriever,
        project_id=project.id,
        query="alpha graph smoke",
        limit=2,
        metadata_filter=RetrievalMetadataFilter(source_type="markdown"),
        monotonic=_monotonic(10.0, 10.042),
    )

    assert provider.inputs == ["alpha graph smoke"]
    assert graph_retriever.requests == [
        {
            "project_id": project.id,
            "seed_chunk_ids": (dense_seed.id, graph_hit.id),
            "limit": 2,
        }
    ]
    assert report.project_id == project.id
    assert report.backend == "neo4j"
    assert report.status == "ready"
    assert report.requested_strategy == "graph"
    assert report.result_count == 1
    assert report.graph_result_count == 1
    assert report.citation_count == 1
    assert report.fallback_reason is None
    assert report.latency_ms == 42
    assert report.limit == 2
    assert report.chunk_ids == (graph_hit.id,)
    assert report.source_external_ids == ("graph.md",)


def test_run_graph_retrieval_smoke_reports_fallback_reason() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    _source, _document, _version, dense_seed = _create_chunk(
        session,
        project=project,
        source_type="markdown",
        external_id="dense.md",
        tags=("docs",),
        stable_id="dense-doc",
        text="Dense seed evidence",
        snippet="Dense seed evidence",
        embedding=_vector(0.1),
    )
    session.add(GraphProjection(project_id=project.id, status="ready"))
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    graph_retriever = RecordingGraphRetriever(
        (),
        failure=GraphStoreUnavailableError("neo4j graph store unavailable"),
    )

    report = run_graph_retrieval_smoke(
        session=session,
        provider=provider,
        graph_retriever=graph_retriever,
        project_id=project.id,
        query="alpha graph smoke",
        limit=1,
        monotonic=_monotonic(20.0, 20.5),
    )

    assert graph_retriever.requests == [
        {
            "project_id": project.id,
            "seed_chunk_ids": (dense_seed.id,),
            "limit": 1,
        }
    ]
    assert report.status == "fallback"
    assert report.result_count == 1
    assert report.graph_result_count == 0
    assert report.citation_count == 1
    assert report.fallback_reason == "graph_store_unavailable"
    assert report.latency_ms == 500


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
            GraphProjection.__table__,
        ],
    )
    return create_session_factory(engine)()


def _create_chunk(
    session: Session,
    *,
    project: Project,
    source_type: str,
    external_id: str,
    tags: tuple[str, ...],
    stable_id: str,
    text: str,
    snippet: str,
    embedding: list[float],
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
    session.flush()
    return source, document, version, chunk


def _vector(first: float, second: float = 0.0) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = first
    values[1] = second
    return values


def _monotonic(*values: float) -> Callable[[], float]:
    active_values = iter(values)
    return lambda: next(active_values)
