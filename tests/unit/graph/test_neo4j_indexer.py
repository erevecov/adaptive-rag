from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from neo4j.exceptions import ServiceUnavailable

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Chunk, Document, DocumentVersion, Project, Source
from adaptive_rag.db.repositories import (
    ChunkRepository,
    DocumentRepository,
    ProjectRepository,
    SourceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.graph import GraphStoreUnavailableError, Neo4jGraphStore
from adaptive_rag.graph.indexer import Neo4jProjectGraph, load_project_graph


class RecordingNeo4jDriver:
    def __init__(
        self,
        *,
        failure: Exception | None = None,
        fail_on_call: int | None = None,
    ) -> None:
        self.failure = failure
        self.fail_on_call = fail_on_call
        self.queries: list[tuple[str, dict[str, Any]]] = []
        self.verify_calls = 0
        self.close_calls = 0

    def verify_connectivity(self) -> None:
        self.verify_calls += 1

    def execute_query(self, query: str, **parameters: Any) -> object:
        self.queries.append((query, parameters))
        if self.failure is not None and len(self.queries) == self.fail_on_call:
            raise self.failure
        return object()

    def close(self) -> None:
        self.close_calls += 1


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


def _sample_graph(project_id: UUID) -> Neo4jProjectGraph:
    source_id = uuid4()
    document_id = uuid4()
    version_id = uuid4()
    first_chunk_id = uuid4()
    second_chunk_id = uuid4()
    return Neo4jProjectGraph(
        project={
            "id": str(project_id),
            "project_id": str(project_id),
            "name": "Demo",
            "embedding_mode": "dense_sparse",
            "retrieval_contextualization_enabled": True,
            "budget_config_json": None,
        },
        sources=(
            {
                "id": str(source_id),
                "project_id": str(project_id),
                "source_type": "markdown",
                "external_id": "alpha.md",
                "tags": ["docs"],
                "extra_metadata_json": '{"title":"Alpha"}',
            },
        ),
        documents=(
            {
                "id": str(document_id),
                "project_id": str(project_id),
                "source_id": str(source_id),
                "stable_id": "alpha",
            },
        ),
        document_versions=(
            {
                "id": str(version_id),
                "project_id": str(project_id),
                "document_id": str(document_id),
                "version_number": 1,
                "content_hash": "sha256:content",
                "index_fingerprint": "sha256:index",
                "parser_metadata_json": None,
                "extraction_metadata_json": '{"lang":"en"}',
            },
        ),
        chunks=(
            {
                "id": str(first_chunk_id),
                "project_id": str(project_id),
                "document_version_id": str(version_id),
                "ordinal": 0,
                "char_start": 0,
                "char_end": 12,
                "token_count": 3,
                "section_metadata_json": '{"heading":"Intro"}',
                "chunker_metadata_json": '{"chunker_version":"semantic_markdown_v1"}',
                "embedding_metadata_json": None,
                "contextual_summary": "Intro context",
            },
            {
                "id": str(second_chunk_id),
                "project_id": str(project_id),
                "document_version_id": str(version_id),
                "ordinal": 1,
                "char_start": 13,
                "char_end": 30,
                "token_count": 4,
                "section_metadata_json": '{"heading":"Details"}',
                "chunker_metadata_json": '{"chunker_version":"semantic_markdown_v1"}',
                "embedding_metadata_json": '{"provider":"fake"}',
                "contextual_summary": None,
            },
        ),
        chunk_links=(
            {
                "from_chunk_id": str(first_chunk_id),
                "to_chunk_id": str(second_chunk_id),
            },
        ),
    )


def test_load_project_graph_serializes_project_graph() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(
        name="Demo",
        budget_config_json={"tier": "test"},
    )
    other_project = ProjectRepository(session).create(name="Other")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="alpha.md",
        tags=["docs"],
        extra_metadata={"title": "Alpha"},
    )
    SourceRepository(session).create(
        project_id=other_project.id,
        source_type="markdown",
        external_id="other.md",
    )
    document = DocumentRepository(session).create_document(
        project_id=project.id,
        source_id=source.id,
        stable_id="alpha",
    )
    version = DocumentRepository(session).create_version(
        project_id=project.id,
        document_id=document.id,
        version_number=1,
        normalized_text="Alpha text with two chunks.",
        content_hash="sha256:content",
        index_fingerprint="sha256:index",
        parser_metadata={"parser": "markdown"},
        extraction_metadata={"lang": "en"},
    )
    chunk_repo = ChunkRepository(session)
    first_chunk = chunk_repo.create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=0,
        char_end=10,
        token_count=2,
        section_metadata={"heading": "Intro"},
        chunker_metadata={"chunker_version": "semantic_markdown_v1"},
        contextual_summary="Intro context",
    )
    second_chunk = chunk_repo.create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=1,
        char_start=11,
        char_end=24,
        token_count=3,
        section_metadata={"heading": "Details"},
        chunker_metadata={"chunker_version": "semantic_markdown_v1"},
    )
    first_chunk.next_chunk_id = second_chunk.id
    second_chunk.prev_chunk_id = first_chunk.id
    chunk_repo.update_dense_embedding(
        project_id=project.id,
        chunk_id=second_chunk.id,
        embedding=[0.1, 0.2],
        embedding_metadata={"provider": "fake"},
    )
    session.flush()

    graph = load_project_graph(session, project.id)

    assert graph.project == {
        "id": str(project.id),
        "project_id": str(project.id),
        "name": "Demo",
        "embedding_mode": "dense_sparse",
        "retrieval_contextualization_enabled": True,
        "budget_config_json": '{"tier":"test"}',
    }
    assert graph.sources == (
        {
            "id": str(source.id),
            "project_id": str(project.id),
            "source_type": "markdown",
            "external_id": "alpha.md",
            "tags": ["docs"],
            "extra_metadata_json": '{"title":"Alpha"}',
        },
    )
    assert graph.documents == (
        {
            "id": str(document.id),
            "project_id": str(project.id),
            "source_id": str(source.id),
            "stable_id": "alpha",
        },
    )
    assert graph.document_versions == (
        {
            "id": str(version.id),
            "project_id": str(project.id),
            "document_id": str(document.id),
            "version_number": 1,
            "content_hash": "sha256:content",
            "index_fingerprint": "sha256:index",
            "parser_metadata_json": '{"parser":"markdown"}',
            "extraction_metadata_json": '{"lang":"en"}',
        },
    )
    assert [chunk["ordinal"] for chunk in graph.chunks] == [0, 1]
    assert graph.chunks[0]["contextual_summary"] == "Intro context"
    assert graph.chunks[1]["embedding_metadata_json"] == '{"provider":"fake"}'
    assert graph.chunk_links == (
        {
            "from_chunk_id": str(first_chunk.id),
            "to_chunk_id": str(second_chunk.id),
        },
    )


def test_neo4j_backfill_replaces_project_scope_then_upserts_graph_payload() -> None:
    project_id = uuid4()
    loaded_projects: list[UUID] = []
    driver = RecordingNeo4jDriver()

    def loader(active_project_id: UUID) -> Neo4jProjectGraph:
        loaded_projects.append(active_project_id)
        return _sample_graph(active_project_id)

    store = Neo4jGraphStore(driver=driver, project_graph_loader=loader)

    result = store.backfill_project_graph(
        project_id=project_id,
        source_watermark="chunks:v2",
    )

    assert result.project_id == project_id
    assert result.backend == "neo4j"
    assert result.status == "ready"
    assert result.source_watermark == "chunks:v2"
    assert result.node_count == 6
    assert result.relationship_count == 6
    assert loaded_projects == [project_id]
    assert [set(parameters) for _, parameters in driver.queries] == [
        {"project_id"},
        {"project", "source_watermark"},
        {"sources"},
        {"documents"},
        {"document_versions"},
        {"chunks"},
        {"chunk_links"},
    ]
    assert "DETACH DELETE" in driver.queries[0][0]
    assert driver.queries[0][1] == {"project_id": str(project_id)}
    assert driver.queries[1][1]["project"]["id"] == str(project_id)
    assert driver.queries[1][1]["source_watermark"] == "chunks:v2"
    assert driver.queries[2][1]["sources"][0]["extra_metadata_json"] == (
        '{"title":"Alpha"}'
    )
    assert driver.queries[6][1]["chunk_links"][0]["from_chunk_id"] != (
        driver.queries[6][1]["chunk_links"][0]["to_chunk_id"]
    )


def test_neo4j_delete_project_graph_removes_only_project_scoped_graph_nodes() -> None:
    project_id = uuid4()
    driver = RecordingNeo4jDriver()
    store = Neo4jGraphStore(
        driver=driver,
        project_graph_loader=lambda active_project_id: _sample_graph(
            active_project_id
        ),
    )

    store.delete_project_graph(project_id=project_id)

    assert len(driver.queries) == 1
    query, parameters = driver.queries[0]
    assert "MATCH (n:AdaptiveRagGraph {project_id: $project_id})" in query
    assert "DETACH DELETE" in query
    assert parameters == {"project_id": str(project_id)}


def test_neo4j_backfill_maps_driver_unavailable_to_stable_error() -> None:
    driver = RecordingNeo4jDriver(
        failure=ServiceUnavailable("network outage"),
        fail_on_call=2,
    )
    store = Neo4jGraphStore(
        driver=driver,
        project_graph_loader=lambda active_project_id: _sample_graph(
            active_project_id
        ),
    )

    with pytest.raises(GraphStoreUnavailableError) as exc_info:
        store.backfill_project_graph(
            project_id=uuid4(),
            source_watermark="chunks:v2",
        )

    assert exc_info.value.error_code == "graph_store_unavailable"
