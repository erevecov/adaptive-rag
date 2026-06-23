"""Tests del comando CLI de retrieval."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from typer.testing import CliRunner

from adaptive_rag.cli.app import app
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


class RecordingRerankProvider:
    provider_name = "fake-rerank"
    model_name = "cli-rerank-v1"

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
            GraphProjection.__table__,
        ],
    )
    return create_session_factory(engine)()


def _vector(first: float, second: float = 0.0) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = first
    values[1] = second
    return values


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


def _patch_retrieval_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session: Session,
    provider: StaticQueryEmbeddingProvider,
    reranker: RecordingRerankProvider | None = None,
    graph_retriever: RecordingGraphRetriever | None = None,
) -> None:
    @contextmanager
    def override_session_scope() -> Iterator[Session]:
        yield session

    monkeypatch.setattr(
        "adaptive_rag.cli.retrieval.session_scope",
        override_session_scope,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.retrieval.get_cli_dense_embedding_provider",
        lambda: provider,
    )
    if reranker is not None:
        monkeypatch.setattr(
            "adaptive_rag.cli.retrieval.get_cli_rerank_provider",
            lambda: reranker,
        )
    monkeypatch.setattr(
        "adaptive_rag.cli.retrieval.get_cli_graph_retriever",
        lambda: graph_retriever,
    )


def test_retrieval_search_command_outputs_json_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    _patch_retrieval_dependencies(monkeypatch, session=session, provider=provider)

    result = CliRunner().invoke(
        app,
        [
            "retrieval",
            "search",
            "--project-id",
            str(project.id),
            "--query",
            "alpha question",
            "--limit",
            "5",
            "--source-type",
            "markdown",
            "--tag",
            "docs",
            "--tag",
            "v1",
        ],
    )

    assert result.exit_code == 0
    assert provider.inputs == ["alpha question"]
    data = json.loads(result.stdout)
    assert [item["chunk_id"] for item in data["results"]] == [
        str(near.id),
        str(far.id),
    ]
    first = data["results"][0]
    assert first["distance"] == pytest.approx(0.1)
    assert first["score"] == pytest.approx(1 / 1.1)
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


def test_retrieval_search_command_reranks_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
                score=0.98,
                original_rank=2,
                rerank_rank=1,
            ),
        )
    )
    _patch_retrieval_dependencies(
        monkeypatch,
        session=session,
        provider=provider,
        reranker=reranker,
    )

    result = CliRunner().invoke(
        app,
        [
            "retrieval",
            "search",
            "--project-id",
            str(project.id),
            "--query",
            "beta question",
            "--limit",
            "1",
            "--rerank-candidate-limit",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert provider.inputs == ["beta question"]
    assert len(reranker.requests) == 1
    candidate_ids = [
        candidate.candidate_id for candidate in reranker.requests[0].candidates
    ]
    assert candidate_ids == [str(near.id), str(mid.id)]
    assert str(far.id) not in {
        candidate.candidate_id for candidate in reranker.requests[0].candidates
    }
    data = json.loads(result.stdout)
    assert [item["chunk_id"] for item in data["results"]] == [str(mid.id)]
    assert data["results"][0]["rerank_metadata"] == {
        "candidate_limit": 2,
        "dense_rank": 2,
        "rerank_model": "cli-rerank-v1",
        "rerank_provider": "fake-rerank",
        "rerank_rank": 1,
        "rerank_score": 0.98,
        "score_metadata": {},
        "used_rerank": True,
    }


def test_retrieval_search_command_uses_lexical_strategy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    _patch_retrieval_dependencies(monkeypatch, session=session, provider=provider)

    result = CliRunner().invoke(
        app,
        [
            "retrieval",
            "search",
            "--project-id",
            str(project.id),
            "--query",
            "SKU-42 installation",
            "--limit",
            "2",
            "--strategy",
            "lexical",
        ],
    )

    assert result.exit_code == 0
    assert provider.inputs == []
    data = json.loads(result.stdout)
    assert [item["chunk_id"] for item in data["results"]] == [
        str(target.id),
        str(general.id),
    ]
    assert data["results"][0]["strategy"] == "lexical"
    assert data["results"][0]["retrieval_metadata"] == {
        "lexical_rank": 1,
        "lexical_score": 3.0,
        "used_lexical": True,
    }


def test_retrieval_search_command_uses_hybrid_rrf_strategy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    _patch_retrieval_dependencies(monkeypatch, session=session, provider=provider)

    result = CliRunner().invoke(
        app,
        [
            "retrieval",
            "search",
            "--project-id",
            str(project.id),
            "--query",
            "SKU-42 installation",
            "--limit",
            "2",
            "--strategy",
            "hybrid_rrf",
        ],
    )

    assert result.exit_code == 0
    assert provider.inputs == ["SKU-42 installation"]
    data = json.loads(result.stdout)
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


def test_retrieval_search_command_uses_graph_strategy_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    _patch_retrieval_dependencies(
        monkeypatch,
        session=session,
        provider=provider,
        graph_retriever=graph_retriever,
    )

    result = CliRunner().invoke(
        app,
        [
            "retrieval",
            "search",
            "--project-id",
            str(project.id),
            "--query",
            "alpha question",
            "--limit",
            "1",
            "--strategy",
            "graph",
        ],
    )

    assert result.exit_code == 0
    assert provider.inputs == ["alpha question"]
    assert graph_retriever.requests == [
        {
            "project_id": project.id,
            "seed_chunk_ids": (near.id,),
            "limit": 1,
        }
    ]
    data = json.loads(result.stdout)
    assert [item["chunk_id"] for item in data["results"]] == [str(far.id)]
    assert data["results"][0]["strategy"] == "graph"
    assert "fallback_reason" not in data["results"][0]


def test_retrieval_search_command_rejects_invalid_rerank_limit_before_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    reranker = RecordingRerankProvider(scores=())
    _patch_retrieval_dependencies(
        monkeypatch,
        session=session,
        provider=provider,
        reranker=reranker,
    )

    result = CliRunner().invoke(
        app,
        [
            "retrieval",
            "search",
            "--project-id",
            str(project.id),
            "--query",
            "alpha question",
            "--limit",
            "2",
            "--rerank-candidate-limit",
            "1",
        ],
    )

    assert result.exit_code == 1
    assert "rerank candidate_limit must be greater than or equal to limit" in (
        result.output
    )
    assert provider.inputs == []
    assert reranker.requests == []


def test_retrieval_search_command_reports_service_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    project = _create_project(session)
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    _patch_retrieval_dependencies(monkeypatch, session=session, provider=provider)

    result = CliRunner().invoke(
        app,
        [
            "retrieval",
            "search",
            "--project-id",
            str(project.id),
            "--query",
            " ",
        ],
    )

    assert result.exit_code == 1
    assert "query must not be empty" in result.output
    assert provider.inputs == []

