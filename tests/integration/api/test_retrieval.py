"""Tests de la superficie HTTP de retrieval."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import (
    get_dense_embedding_provider,
    get_graph_retriever,
    get_rerank_provider_factory,
    get_session,
    get_sparse_embedding_provider_factory,
)
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    EMBEDDING_DIMENSIONS,
    Chunk,
    ChunkSparseEmbedding,
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
    SparseEmbeddingRepository,
)
from adaptive_rag.db.session import create_session_factory
from adaptive_rag.embeddings import SparseEmbeddingVector
from adaptive_rag.graph import GraphRetrievalResult
from adaptive_rag.rerank import RerankRequest, RerankResult, RerankScore


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


class StaticSparseEmbeddingProvider:
    provider_name = "fake"
    model_name = "static-sparse-v1"
    dimensions = EMBEDDING_DIMENSIONS

    def __init__(self, query_vector: SparseEmbeddingVector) -> None:
        self.query_vector = query_vector
        self.query_inputs: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[SparseEmbeddingVector]:
        return [self.query_vector for _text in texts]

    def embed_query(self, text: str) -> SparseEmbeddingVector:
        self.query_inputs.append(text)
        return self.query_vector


class RecordingRerankProvider:
    provider_name = "fake-rerank"
    model_name = "api-rerank-v1"

    def __init__(self, scores: tuple[RerankScore, ...]) -> None:
        self.scores = scores
        self.requests: list[RerankRequest] = []

    def rerank(self, request: RerankRequest) -> RerankResult:
        self.requests.append(request)
        return RerankResult(
            provider_name=self.provider_name,
            model_name=self.model_name,
            scores=self.scores,
        )


class RecordingGraphRetriever:
    def __init__(self, results: tuple[GraphRetrievalResult, ...]) -> None:
        self.results = results
        self.requests: list[dict[str, object]] = []

    def expand_project_chunks(
        self,
        *,
        project_id,
        seed_chunk_ids,
        limit: int,
    ) -> tuple[GraphRetrievalResult, ...]:
        self.requests.append(
            {
                "project_id": project_id,
                "seed_chunk_ids": tuple(seed_chunk_ids),
                "limit": limit,
            }
        )
        return self.results


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
            ChunkSparseEmbedding.__table__,
            GraphProjection.__table__,
        ],
    )
    return create_session_factory(engine)()


def _vector(first: float, second: float = 0.0) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = first
    values[1] = second
    return values


def _client(
    *,
    session: Session,
    provider: StaticQueryEmbeddingProvider,
    sparse_provider: StaticSparseEmbeddingProvider | None = None,
    rerank_provider_factory: Iterator[RecordingRerankProvider] | None = None,
    graph_retriever: RecordingGraphRetriever | None = None,
) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    def override_provider() -> StaticQueryEmbeddingProvider:
        return provider

    def override_sparse_provider() -> StaticSparseEmbeddingProvider:
        return sparse_provider or StaticSparseEmbeddingProvider(
            SparseEmbeddingVector(indices=(), values=())
        )

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_dense_embedding_provider] = override_provider
    app.dependency_overrides[get_sparse_embedding_provider_factory] = (
        lambda: override_sparse_provider
    )
    if graph_retriever is not None:
        app.dependency_overrides[get_graph_retriever] = lambda: graph_retriever
    if rerank_provider_factory is not None:
        providers = iter(rerank_provider_factory)

        def override_rerank_provider_factory():
            return lambda: next(providers)

        app.dependency_overrides[get_rerank_provider_factory] = (
            override_rerank_provider_factory
        )
    return TestClient(app)


def _create_project(session: Session, name: str = "demo") -> Project:
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
    session.flush()
    return source, document, version, chunk


def _create_sparse_embedding(
    session: Session,
    *,
    project: Project,
    chunk: Chunk,
    indices: tuple[int, ...],
    values: tuple[float, ...],
    fingerprint: str,
) -> None:
    SparseEmbeddingRepository(session).upsert_current(
        project_id=project.id,
        chunk_id=chunk.id,
        vector=SparseEmbeddingVector(indices=indices, values=values),
        input_hash=f"sha256:{fingerprint}",
        index_fingerprint=fingerprint,
        extra_metadata={"provider": "fake"},
    )


def test_retrieval_search_endpoint_returns_results_with_citations() -> None:
    session = _make_session()
    project = _create_project(session)
    _far_source, _far_document, _far_version, far = _create_embedded_chunk(
        session,
        project=project,
        external_id="far.md",
        tags=("docs", "v1"),
        stable_id="far-doc",
        text="Far original evidence",
        snippet="Far original evidence",
        embedding=_vector(0.9),
    )
    source, document, version, near = _create_embedded_chunk(
        session,
        project=project,
        external_id="near.md",
        tags=("docs", "v1"),
        stable_id="near-doc",
        text="Header\n\nAlpha original evidence",
        snippet="Alpha original evidence",
        embedding=_vector(0.1),
    )
    _create_sparse_embedding(
        session,
        project=project,
        chunk=near,
        indices=(1,),
        values=(1.0,),
        fingerprint="near-sparse",
    )
    _create_sparse_embedding(
        session,
        project=project,
        chunk=far,
        indices=(2,),
        values=(0.5,),
        fingerprint="far-sparse",
    )
    _wrong_type_source, _wrong_type_document, _wrong_type_version, _wrong_type = (
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
        )
    )
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    sparse_provider = StaticSparseEmbeddingProvider(
        SparseEmbeddingVector(indices=(1, 2), values=(1.0, 0.1))
    )
    client = _client(
        session=session,
        provider=provider,
        sparse_provider=sparse_provider,
    )

    response = client.post(
        f"/projects/{project.id}/retrieval/search",
        json={
            "query": "alpha question",
            "limit": 5,
            "metadata_filter": {
                "source_type": "markdown",
                "tags": ["docs", "v1"],
            },
        },
    )

    assert response.status_code == 200
    assert provider.inputs == ["alpha question"]
    assert sparse_provider.query_inputs == ["alpha question"]
    data = response.json()
    assert [result["chunk_id"] for result in data["results"]] == [
        str(near.id),
        str(far.id),
    ]
    first = data["results"][0]
    assert first["distance"] == pytest.approx(1 / (1 + (2 / 61)))
    assert first["score"] == pytest.approx(2 / 61)
    assert first["embedding_metadata"] is None
    assert first["strategy"] == "dense_sparse"
    assert first["retrieval_metadata"]["source_strategies"] == ["dense", "sparse"]
    assert "fallback_reason" not in first
    assert "rerank_metadata" not in first
    assert first["citation"] == {
        "source_id": str(source.id),
        "source_type": "markdown",
        "source_external_id": "near.md",
        "source_tags": ["docs", "v1"],
        "source_extra_metadata": {"title": "near.md"},
        "document_id": str(document.id),
        "document_stable_id": "near-doc",
        "document_version_id": str(version.id),
        "document_version_number": 1,
        "chunk_id": str(near.id),
        "char_start": 8,
        "char_end": 31,
        "snippet": "Alpha original evidence",
        "section_metadata": {
            "heading": "near-doc",
            "section_path": ["near-doc"],
        },
    }


def test_retrieval_search_endpoint_reranks_when_requested() -> None:
    session = _make_session()
    project = _create_project(session)
    _far_source, _far_document, _far_version, far = _create_embedded_chunk(
        session,
        project=project,
        external_id="far.md",
        stable_id="far-doc",
        text="Far original evidence",
        snippet="Far original evidence",
        embedding=_vector(0.9),
    )
    _mid_source, _mid_document, _mid_version, mid = _create_embedded_chunk(
        session,
        project=project,
        external_id="mid.md",
        stable_id="mid-doc",
        text="Header\n\nBeta rerank evidence",
        snippet="Beta rerank evidence",
        embedding=_vector(0.2),
    )
    _near_source, _near_document, _near_version, near = _create_embedded_chunk(
        session,
        project=project,
        external_id="near.md",
        stable_id="near-doc",
        text="Header\n\nAlpha dense evidence",
        snippet="Alpha dense evidence",
        embedding=_vector(0.1),
    )
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    reranker = RecordingRerankProvider(
        scores=(
            RerankScore(
                candidate_id=str(mid.id),
                score=0.99,
                original_rank=2,
                rerank_rank=1,
                metadata={"request_id": "api-rerank-request"},
            ),
        )
    )
    client = _client(
        session=session,
        provider=provider,
        rerank_provider_factory=iter((reranker,)),
    )

    response = client.post(
        f"/projects/{project.id}/retrieval/search",
        json={
            "query": "beta question",
            "limit": 1,
            "rerank": {"candidate_limit": 2},
        },
    )

    assert response.status_code == 200
    assert provider.inputs == ["beta question"]
    assert len(reranker.requests) == 1
    candidate_ids = [
        candidate.candidate_id for candidate in reranker.requests[0].candidates
    ]
    assert candidate_ids == [str(near.id), str(mid.id)]
    assert str(far.id) not in {
        candidate.candidate_id for candidate in reranker.requests[0].candidates
    }
    data = response.json()
    assert [result["chunk_id"] for result in data["results"]] == [str(mid.id)]
    assert data["results"][0]["rerank_metadata"] == {
        "candidate_limit": 2,
        "dense_rank": 2,
        "rerank_model": "api-rerank-v1",
        "rerank_provider": "fake-rerank",
        "rerank_rank": 1,
        "rerank_score": 0.99,
        "score_metadata": {"request_id": "api-rerank-request"},
        "used_rerank": True,
    }


def test_retrieval_search_endpoint_uses_lexical_strategy_when_requested() -> None:
    session = _make_session()
    project = _create_project(session)
    _general_source, _general_document, _general_version, general = (
        _create_embedded_chunk(
            session,
            project=project,
            external_id="general.md",
            stable_id="general-doc",
            text="General installation notes",
            snippet="General installation notes",
            embedding=None,
        )
    )
    _target_source, _target_document, _target_version, target = (
        _create_embedded_chunk(
            session,
            project=project,
            external_id="target.md",
            stable_id="target-doc",
            text="Header\n\nInstall the connector with the default path.",
            snippet="Install the connector with the default path.",
            embedding=None,
            contextual_summary="SKU-42 connector installation reference.",
        )
    )
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    client = _client(session=session, provider=provider)

    response = client.post(
        f"/projects/{project.id}/retrieval/search",
        json={
            "query": "SKU-42 installation",
            "limit": 2,
            "strategy": "lexical",
        },
    )

    assert response.status_code == 200
    assert provider.inputs == []
    data = response.json()
    assert [result["chunk_id"] for result in data["results"]] == [
        str(target.id),
        str(general.id),
    ]
    assert data["results"][0]["strategy"] == "lexical"
    assert data["results"][0]["retrieval_metadata"] == {
        "lexical_rank": 1,
        "lexical_score": 3.0,
        "used_lexical": True,
    }
    assert data["results"][0]["citation"]["snippet"] == (
        "Install the connector with the default path."
    )


def test_retrieval_search_endpoint_uses_bm25_strategy_when_requested() -> None:
    session = _make_session()
    project = _create_project(session)
    filler = " ".join(f"filler{i}" for i in range(80))
    _long_source, _long_document, _long_version, long_match = (
        _create_embedded_chunk(
            session,
            project=project,
            external_id="long.md",
            stable_id="long-doc",
            text=f"SKU 42 manual {filler}",
            snippet=f"SKU 42 manual {filler}",
            embedding=None,
        )
    )
    _short_source, _short_document, _short_version, short_match = (
        _create_embedded_chunk(
            session,
            project=project,
            external_id="short.md",
            stable_id="short-doc",
            text="Header\n\nSKU 42 manual",
            snippet="SKU 42 manual",
            embedding=None,
        )
    )
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    sparse_provider = StaticSparseEmbeddingProvider(
        SparseEmbeddingVector(indices=(1, 2), values=(1.0, 0.1))
    )
    client = _client(
        session=session,
        provider=provider,
        sparse_provider=sparse_provider,
    )

    response = client.post(
        f"/projects/{project.id}/retrieval/search",
        json={
            "query": "SKU 42 manual",
            "limit": 2,
            "strategy": "bm25",
        },
    )

    assert response.status_code == 200
    assert provider.inputs == []
    data = response.json()
    assert [result["chunk_id"] for result in data["results"]] == [
        str(short_match.id),
        str(long_match.id),
    ]
    assert data["results"][0]["strategy"] == "bm25"
    assert data["results"][0]["retrieval_metadata"] == {
        "bm25_rank": 1,
        "bm25_score": data["results"][0]["score"],
        "used_bm25": True,
    }


def test_retrieval_search_endpoint_uses_hybrid_rrf_strategy_when_requested() -> None:
    session = _make_session()
    project = _create_project(session)
    _general_source, _general_document, _general_version, _general = (
        _create_embedded_chunk(
            session,
            project=project,
            external_id="general.md",
            stable_id="general-doc",
            text="General installation notes",
            snippet="General installation notes",
            embedding=_vector(0.9),
        )
    )
    _target_source, _target_document, _target_version, target = (
        _create_embedded_chunk(
            session,
            project=project,
            external_id="target.md",
            stable_id="target-doc",
            text="Header\n\nInstall the connector with the default path.",
            snippet="Install the connector with the default path.",
            embedding=_vector(0.1),
            contextual_summary="SKU-42 connector installation reference.",
        )
    )
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    client = _client(session=session, provider=provider)

    response = client.post(
        f"/projects/{project.id}/retrieval/search",
        json={
            "query": "SKU-42 installation",
            "limit": 2,
            "strategy": "hybrid_rrf",
        },
    )

    assert response.status_code == 200
    assert provider.inputs == ["SKU-42 installation"]
    data = response.json()
    assert data["results"][0]["chunk_id"] == str(target.id)
    assert data["results"][0]["strategy"] == "hybrid_rrf"
    assert data["results"][0]["retrieval_metadata"] == {
        "rrf_k": 60,
        "rrf_score": pytest.approx(2 / 61),
        "source_strategies": ["dense", "lexical"],
        "used_rrf": True,
        "dense_rank": 1,
        "dense_score": pytest.approx(1 / 1.1),
        "lexical_rank": 1,
        "lexical_score": 3.0,
    }


def test_retrieval_search_endpoint_uses_dense_sparse_strategy_when_requested() -> None:
    session = _make_session()
    project = _create_project(session)
    _general_source, _general_document, _general_version, _general = (
        _create_embedded_chunk(
            session,
            project=project,
            external_id="general.md",
            stable_id="general-doc",
            text="General installation notes",
            snippet="General installation notes",
            embedding=_vector(0.1),
        )
    )
    _target_source, _target_document, _target_version, target = (
        _create_embedded_chunk(
            session,
            project=project,
            external_id="target.md",
            stable_id="target-doc",
            text="Header\n\nInstall the connector with the default path.",
            snippet="Install the connector with the default path.",
            embedding=_vector(0.4),
            contextual_summary="SKU-42 connector installation reference.",
        )
    )
    _create_sparse_embedding(
        session,
        project=project,
        chunk=target,
        indices=(42,),
        values=(3.0,),
        fingerprint="sparse-fp:target",
    )
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    sparse_provider = StaticSparseEmbeddingProvider(
        SparseEmbeddingVector(indices=(42,), values=(1.0,))
    )
    client = _client(
        session=session,
        provider=provider,
        sparse_provider=sparse_provider,
    )

    response = client.post(
        f"/projects/{project.id}/retrieval/search",
        json={
            "query": "SKU-42 installation",
            "limit": 2,
            "strategy": "dense_sparse",
        },
    )

    assert response.status_code == 200
    assert provider.inputs == ["SKU-42 installation"]
    assert sparse_provider.query_inputs == ["SKU-42 installation"]
    data = response.json()
    assert data["results"][0]["chunk_id"] == str(target.id)
    assert data["results"][0]["strategy"] == "dense_sparse"
    assert data["results"][0]["retrieval_metadata"] == {
        "rrf_k": 60,
        "rrf_score": pytest.approx((1 / 62) + (1 / 61)),
        "source_strategies": ["dense", "sparse"],
        "used_rrf": True,
        "dense_rank": 2,
        "dense_score": pytest.approx(1 / 1.4),
        "sparse_rank": 1,
        "sparse_score": 3.0,
        "sparse_index_fingerprint": "sparse-fp:target",
    }


def test_retrieval_search_endpoint_uses_sparse_strategy_when_requested() -> None:
    session = _make_session()
    project = _create_project(session)
    _general_source, _general_document, _general_version, _general = (
        _create_embedded_chunk(
            session,
            project=project,
            external_id="general.md",
            stable_id="general-doc",
            text="General installation notes",
            snippet="General installation notes",
            embedding=_vector(0.1),
        )
    )
    _target_source, _target_document, _target_version, target = (
        _create_embedded_chunk(
            session,
            project=project,
            external_id="target.md",
            stable_id="target-doc",
            text="Header\n\nInstall the connector with the default path.",
            snippet="Install the connector with the default path.",
            embedding=_vector(0.4),
            contextual_summary="SKU-42 connector installation reference.",
        )
    )
    _create_sparse_embedding(
        session,
        project=project,
        chunk=target,
        indices=(42,),
        values=(3.0,),
        fingerprint="sparse-fp:target",
    )
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    sparse_provider = StaticSparseEmbeddingProvider(
        SparseEmbeddingVector(indices=(42,), values=(1.0,))
    )
    client = _client(
        session=session,
        provider=provider,
        sparse_provider=sparse_provider,
    )

    response = client.post(
        f"/projects/{project.id}/retrieval/search",
        json={
            "query": "SKU-42 installation",
            "limit": 2,
            "strategy": "sparse",
        },
    )

    assert response.status_code == 200
    assert provider.inputs == []
    assert sparse_provider.query_inputs == ["SKU-42 installation"]
    data = response.json()
    assert [result["chunk_id"] for result in data["results"]] == [str(target.id)]
    assert data["results"][0]["strategy"] == "sparse"
    assert data["results"][0]["retrieval_metadata"] == {
        "sparse_index_fingerprint": "sparse-fp:target",
        "sparse_rank": 1,
        "sparse_score": 3.0,
        "used_sparse": True,
    }


def test_retrieval_search_endpoint_uses_graph_strategy_when_requested() -> None:
    session = _make_session()
    project = _create_project(session)
    _far_source, _far_document, _far_version, far = _create_embedded_chunk(
        session,
        project=project,
        external_id="far.md",
        stable_id="far-doc",
        text="Far graph-expanded evidence",
        snippet="Far graph-expanded evidence",
        embedding=_vector(0.9),
    )
    _near_source, _near_document, _near_version, near = _create_embedded_chunk(
        session,
        project=project,
        external_id="near.md",
        stable_id="near-doc",
        text="Header\n\nAlpha dense seed evidence",
        snippet="Alpha dense seed evidence",
        embedding=_vector(0.1),
    )
    session.add(GraphProjection(project_id=project.id, status="ready"))
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    graph_retriever = RecordingGraphRetriever(
        (GraphRetrievalResult(chunk_id=far.id, distance=1.0, score=0.5),)
    )
    client = _client(
        session=session,
        provider=provider,
        graph_retriever=graph_retriever,
    )

    response = client.post(
        f"/projects/{project.id}/retrieval/search",
        json={"query": "alpha question", "limit": 1, "strategy": "graph"},
    )

    assert response.status_code == 200
    assert provider.inputs == ["alpha question"]
    assert graph_retriever.requests == [
        {
            "project_id": project.id,
            "seed_chunk_ids": (near.id,),
            "limit": 1,
        }
    ]
    data = response.json()
    assert [result["chunk_id"] for result in data["results"]] == [str(far.id)]
    assert data["results"][0]["strategy"] == "graph"
    assert "fallback_reason" not in data["results"][0]


def test_retrieval_search_endpoint_reports_graph_fallback_reason() -> None:
    session = _make_session()
    project = _create_project(session)
    _far_source, _far_document, _far_version, far = _create_embedded_chunk(
        session,
        project=project,
        external_id="far.md",
        stable_id="far-doc",
        text="Far original evidence",
        snippet="Far original evidence",
        embedding=_vector(0.9),
    )
    _near_source, _near_document, _near_version, near = _create_embedded_chunk(
        session,
        project=project,
        external_id="near.md",
        stable_id="near-doc",
        text="Header\n\nAlpha dense evidence",
        snippet="Alpha dense evidence",
        embedding=_vector(0.1),
    )
    session.add(GraphProjection(project_id=project.id, status="pending_backfill"))
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    graph_retriever = RecordingGraphRetriever(())
    client = _client(
        session=session,
        provider=provider,
        graph_retriever=graph_retriever,
    )

    response = client.post(
        f"/projects/{project.id}/retrieval/search",
        json={"query": "alpha question", "limit": 2, "strategy": "graph"},
    )

    assert response.status_code == 200
    assert graph_retriever.requests == []
    data = response.json()
    assert [result["chunk_id"] for result in data["results"]] == [
        str(near.id),
        str(far.id),
    ]
    assert [result["strategy"] for result in data["results"]] == ["dense", "dense"]
    assert [result["fallback_reason"] for result in data["results"]] == [
        "graph_projection_pending_backfill",
        "graph_projection_pending_backfill",
    ]


def test_retrieval_search_endpoint_rejects_invalid_rerank_limit_before_provider() -> (
    None
):
    session = _make_session()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    reranker = RecordingRerankProvider(scores=())
    client = _client(
        session=session,
        provider=provider,
        rerank_provider_factory=iter((reranker,)),
    )

    response = client.post(
        f"/projects/{project.id}/retrieval/search",
        json={
            "query": "alpha question",
            "limit": 2,
            "rerank": {"candidate_limit": 1},
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "rerank candidate_limit must be greater than or equal to limit"
    }
    assert provider.inputs == []
    assert reranker.requests == []


def test_retrieval_search_endpoint_rejects_unknown_filter_fields() -> None:
    session = _make_session()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    client = _client(session=session, provider=provider)

    response = client.post(
        f"/projects/{project.id}/retrieval/search",
        json={
            "query": "alpha question",
            "metadata_filter": {"unsupported": "value"},
        },
    )

    assert response.status_code == 422
    assert provider.inputs == []


def test_retrieval_search_endpoint_maps_service_errors_to_422() -> None:
    session = _make_session()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    client = _client(session=session, provider=provider)

    response = client.post(
        f"/projects/{project.id}/retrieval/search",
        json={"query": " "},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "query must not be empty"}
    assert provider.inputs == []
