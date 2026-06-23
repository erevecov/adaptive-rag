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
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.graph import GraphRetrievalResult, GraphStoreUnavailableError
from adaptive_rag.provider_usage import ProviderBudgetExceededError
from adaptive_rag.rerank import (
    RerankProviderError,
    RerankRequest,
    RerankResult,
    RerankScore,
)
from adaptive_rag.retrieval import (
    RetrievalMetadataFilter,
    RetrievalRerankOptions,
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


class RecordingRerankProvider:
    provider_name = "fake-rerank"
    model_name = "recording-rerank-v1"

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


class FailingRerankProvider:
    provider_name = "fake-rerank"
    model_name = "failing-rerank-v1"

    def rerank(self, _request: RerankRequest) -> RerankResult:
        raise RerankProviderError("provider unavailable")


class BudgetBlockedRerankProvider:
    provider_name = "fake-rerank"
    model_name = "budget-blocked-rerank-v1"

    def rerank(self, _request: RerankRequest) -> RerankResult:
        raise ProviderBudgetExceededError("provider budget exceeded")


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
        if self.failure is not None:
            raise self.failure
        return self.results


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
            GraphProjection.__table__,
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
    assert results[0].rerank_metadata is None
    assert results[0].strategy == "dense"


def test_retrieval_service_uses_lexical_strategy_without_embedding_query() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    _general_source, _general_document, _general_version, general = (
        _create_embedded_chunk(
            session,
            project=project,
            external_id="general.md",
            stable_id="general",
            text="General installation notes",
            snippet="General installation notes",
            embedding=None,
        )
    )
    _target_source, _target_document, _target_version, target = _create_embedded_chunk(
        session,
        project=project,
        external_id="sku.md",
        stable_id="sku",
        text="Header\n\nInstall the connector with the default path.",
        snippet="Install the connector with the default path.",
        embedding=None,
        contextual_summary="SKU-42 connector installation reference.",
    )
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    session.commit()

    results = RetrievalService(session, provider=provider).search(
        RetrievalSearchRequest(
            project_id=project.id,
            query="SKU-42 installation",
            limit=2,
            strategy="lexical",
        )
    )

    assert provider.inputs == []
    assert [result.chunk_id for result in results] == [target.id, general.id]
    assert [result.strategy for result in results] == ["lexical", "lexical"]
    assert results[0].score > results[1].score
    assert results[0].citation.snippet == "Install the connector with the default path."
    assert results[0].retrieval_metadata == {
        "lexical_rank": 1,
        "lexical_score": results[0].score,
        "used_lexical": True,
    }


def test_retrieval_service_fuses_dense_and_lexical_with_rrf() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    _dense_source, _dense_document, _dense_version, dense_only = (
        _create_embedded_chunk(
            session,
            project=project,
            external_id="dense.md",
            stable_id="dense",
            text="Alpha semantic evidence",
            snippet="Alpha semantic evidence",
            embedding=_vector(0.1),
        )
    )
    _target_source, _target_document, _target_version, target = _create_embedded_chunk(
        session,
        project=project,
        external_id="target.md",
        stable_id="target",
        text="Header\n\nInstall the connector with the default path.",
        snippet="Install the connector with the default path.",
        embedding=_vector(0.4),
        contextual_summary="SKU-42 connector installation reference.",
    )
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    session.commit()

    results = RetrievalService(session, provider=provider).search(
        RetrievalSearchRequest(
            project_id=project.id,
            query="SKU-42 installation",
            limit=2,
            strategy="hybrid_rrf",
        )
    )

    assert provider.inputs == ["SKU-42 installation"]
    assert [result.chunk_id for result in results] == [target.id, dense_only.id]
    assert [result.strategy for result in results] == ["hybrid_rrf", "hybrid_rrf"]
    assert results[0].retrieval_metadata == {
        "dense_rank": 2,
        "dense_score": pytest.approx(1 / 1.4),
        "lexical_rank": 1,
        "lexical_score": 3.0,
        "rrf_k": 60,
        "rrf_score": results[0].score,
        "source_strategies": ["dense", "lexical"],
        "used_rrf": True,
    }
    assert results[1].retrieval_metadata == {
        "dense_rank": 1,
        "dense_score": pytest.approx(1 / 1.1),
        "rrf_k": 60,
        "rrf_score": results[1].score,
        "source_strategies": ["dense"],
        "used_rrf": True,
    }


def test_retrieval_service_uses_graph_strategy_when_projection_is_ready() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    _far_source, _far_document, _far_version, far = _create_embedded_chunk(
        session,
        project=project,
        external_id="far.md",
        stable_id="far",
        text="Far graph-expanded evidence",
        snippet="Far graph-expanded evidence",
        embedding=_vector(0.9),
    )
    _near_source, _near_document, _near_version, near = _create_embedded_chunk(
        session,
        project=project,
        external_id="near.md",
        stable_id="near",
        text="Alpha dense seed evidence",
        snippet="Alpha dense seed evidence",
        embedding=_vector(0.1),
    )
    projection = GraphProjection(
        project_id=project.id,
        status="ready",
        source_watermark="chunks:v1",
    )
    session.add(projection)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    graph_retriever = RecordingGraphRetriever(
        (
            GraphRetrievalResult(chunk_id=far.id, distance=1.0, score=0.5),
            GraphRetrievalResult(chunk_id=near.id, distance=0.0, score=1.0),
        )
    )

    results = RetrievalService(
        session,
        provider=provider,
        graph_retriever=graph_retriever,
    ).search(
        RetrievalSearchRequest(
            project_id=project.id,
            query="alpha question",
            limit=2,
            strategy="graph",
        )
    )

    assert provider.inputs == ["alpha question"]
    assert graph_retriever.requests == [
        {
            "project_id": project.id,
            "seed_chunk_ids": (near.id, far.id),
            "limit": 2,
        }
    ]
    assert [result.chunk_id for result in results] == [far.id, near.id]
    assert [result.strategy for result in results] == ["graph", "graph"]
    assert results[0].distance == pytest.approx(1.0)
    assert results[0].score == pytest.approx(0.5)
    assert results[0].citation.snippet == "Far graph-expanded evidence"


def test_retrieval_service_falls_back_to_dense_when_projection_is_not_ready() -> None:
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
        text="Alpha original evidence",
        snippet="Alpha original evidence",
        embedding=_vector(0.1),
    )
    session.add(GraphProjection(project_id=project.id, status="pending_backfill"))
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    graph_retriever = RecordingGraphRetriever(())

    results = RetrievalService(
        session,
        provider=provider,
        graph_retriever=graph_retriever,
    ).search(
        RetrievalSearchRequest(
            project_id=project.id,
            query="alpha question",
            limit=2,
            strategy="graph",
        )
    )

    assert graph_retriever.requests == []
    assert [result.chunk_id for result in results] == [near.id, far.id]
    assert [result.strategy for result in results] == ["dense", "dense"]
    assert [result.fallback_reason for result in results] == [
        "graph_projection_pending_backfill",
        "graph_projection_pending_backfill",
    ]


def test_retrieval_service_falls_back_to_dense_when_graph_is_unavailable() -> None:
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
        text="Alpha original evidence",
        snippet="Alpha original evidence",
        embedding=_vector(0.1),
    )
    session.add(GraphProjection(project_id=project.id, status="ready"))
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    graph_retriever = RecordingGraphRetriever(
        (),
        failure=GraphStoreUnavailableError("neo4j unavailable"),
    )

    results = RetrievalService(
        session,
        provider=provider,
        graph_retriever=graph_retriever,
    ).search(
        RetrievalSearchRequest(
            project_id=project.id,
            query="alpha question",
            limit=2,
            strategy="graph",
        )
    )

    assert len(graph_retriever.requests) == 1
    assert [result.chunk_id for result in results] == [near.id, far.id]
    assert [result.strategy for result in results] == ["dense", "dense"]
    assert [result.fallback_reason for result in results] == [
        "graph_store_unavailable",
        "graph_store_unavailable",
    ]


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
                limit=2,
                rerank=RetrievalRerankOptions(candidate_limit=1),
            ),
            "rerank candidate_limit must be greater than or equal to limit",
        ),
        (
            RetrievalSearchRequest(
                project_id=PROJECT_ID,
                query="x",
                strategy="unsupported",
            ),
            "retrieval strategy must be dense, graph, lexical or hybrid_rrf",
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


def test_retrieval_service_requires_rerank_provider_when_enabled() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    session.commit()

    with pytest.raises(
        RetrievalServiceError,
        match="rerank provider is required when rerank is enabled",
    ):
        RetrievalService(session, provider=provider).search(
            RetrievalSearchRequest(
                project_id=project.id,
                query="alpha question",
                limit=3,
                rerank=RetrievalRerankOptions(candidate_limit=3),
            )
        )

    assert provider.inputs == []


def test_retrieval_service_reranks_prefiltered_dense_candidates() -> None:
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
    _mid_source, _mid_document, _mid_version, mid = _create_embedded_chunk(
        session,
        project=project,
        external_id="mid.md",
        stable_id="mid",
        text="Header\n\nBeta rerank evidence",
        snippet="Beta rerank evidence",
        embedding=_vector(0.2),
    )
    _near_source, _near_document, _near_version, near = _create_embedded_chunk(
        session,
        project=project,
        external_id="near.md",
        stable_id="near",
        text="Header\n\nAlpha dense evidence",
        snippet="Alpha dense evidence",
        embedding=_vector(0.1),
    )
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    reranker = RecordingRerankProvider(
        scores=(
            RerankScore(
                candidate_id=str(mid.id),
                score=0.99,
                original_rank=2,
                rerank_rank=1,
                metadata={"reason": "lexical match"},
            ),
        )
    )
    session.commit()

    results = RetrievalService(
        session,
        provider=provider,
        reranker=reranker,
    ).search(
        RetrievalSearchRequest(
            project_id=project.id,
            query="beta question",
            limit=1,
            rerank=RetrievalRerankOptions(candidate_limit=2),
        )
    )

    assert provider.inputs == ["beta question"]
    assert len(reranker.requests) == 1
    rerank_request = reranker.requests[0]
    assert rerank_request.query == "beta question"
    assert rerank_request.top_k == 1
    assert [candidate.candidate_id for candidate in rerank_request.candidates] == [
        str(near.id),
        str(mid.id),
    ]
    assert str(far.id) not in {
        candidate.candidate_id for candidate in rerank_request.candidates
    }
    assert [result.chunk_id for result in results] == [mid.id]
    assert results[0].distance == pytest.approx(0.2)
    assert results[0].score == pytest.approx(1 / 1.2)
    assert results[0].citation.snippet == "Beta rerank evidence"
    assert results[0].rerank_metadata == {
        "candidate_limit": 2,
        "dense_rank": 2,
        "rerank_model": "recording-rerank-v1",
        "rerank_provider": "fake-rerank",
        "rerank_rank": 1,
        "rerank_score": 0.99,
        "score_metadata": {"reason": "lexical match"},
        "used_rerank": True,
    }


def test_retrieval_service_maps_rerank_provider_errors() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    _source, _document, _version, _chunk = _create_embedded_chunk(
        session,
        project=project,
        external_id="near.md",
        stable_id="near",
        text="Alpha dense evidence",
        snippet="Alpha dense evidence",
        embedding=_vector(0.1),
    )
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    session.commit()

    with pytest.raises(
        RetrievalServiceError,
        match="rerank failed: provider unavailable",
    ):
        RetrievalService(
            session,
            provider=provider,
            reranker=FailingRerankProvider(),
        ).search(
            RetrievalSearchRequest(
                project_id=project.id,
                query="alpha question",
                limit=1,
                rerank=RetrievalRerankOptions(candidate_limit=1),
            )
        )


def test_retrieval_service_maps_rerank_budget_errors() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    _source, _document, _version, _chunk = _create_embedded_chunk(
        session,
        project=project,
        external_id="near.md",
        stable_id="near",
        text="Alpha dense evidence",
        snippet="Alpha dense evidence",
        embedding=_vector(0.1),
    )
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    session.commit()

    with pytest.raises(
        RetrievalServiceError,
        match="rerank failed: provider budget exceeded",
    ):
        RetrievalService(
            session,
            provider=provider,
            reranker=BudgetBlockedRerankProvider(),
        ).search(
            RetrievalSearchRequest(
                project_id=project.id,
                query="alpha question",
                limit=1,
                rerank=RetrievalRerankOptions(candidate_limit=1),
            )
        )


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
