"""Tests del baseline de embeddings densos.

El pipeline debe usar provider fakes, validar dimension 1024 y persistir
embeddings sobre chunks existentes sin implementar retrieval.
"""

from __future__ import annotations

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
from adaptive_rag.embeddings import (
    DenseEmbeddingPipeline,
    DenseEmbeddingPipelineError,
    FakeDenseEmbeddingProvider,
)


class WrongDimensionProvider:
    provider_name = "fake"
    model_name = "wrong-dim"
    dimensions = 3

    def __init__(self) -> None:
        self.inputs: list[str] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.inputs.extend(texts)
        return [[0.1, 0.2, 0.3] for _text in texts]


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


def _create_document_version(session, *, text: str) -> tuple[Project, DocumentVersion]:
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="guide.md",
        extra_metadata={"content": text},
    )
    document = DocumentRepository(session).create_document(
        project_id=project.id,
        source_id=source.id,
        stable_id=source.external_id,
    )
    version = DocumentRepository(session).create_version(
        project_id=project.id,
        document_id=document.id,
        version_number=1,
        normalized_text=text,
        content_hash="sha256:test",
        index_fingerprint="ingestion-fp",
    )
    session.commit()
    return project, version


def _create_chunks(session, *, project: Project, version: DocumentVersion) -> None:
    repo = ChunkRepository(session)
    first_end = version.normalized_text.index("\n\n")
    second_start = first_end + 2
    repo.create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=0,
        char_end=first_end,
        token_count=3,
        section_metadata={"heading": "Intro", "section_path": ["Intro"]},
        chunker_metadata={"chunker_version": "semantic_markdown_v1"},
        contextual_summary="Intro section explains the pipeline.",
    )
    repo.create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=1,
        char_start=second_start,
        char_end=len(version.normalized_text),
        token_count=4,
        section_metadata={"heading": "Next", "section_path": ["Next"]},
        chunker_metadata={"chunker_version": "semantic_markdown_v1"},
    )
    session.commit()


def _chunks(session, *, project: Project, version: DocumentVersion) -> list[Chunk]:
    return ChunkRepository(session).list_by_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )


def test_embed_document_version_persists_dense_embeddings_and_metadata() -> None:
    text = "Alpha beta gamma\n\nDelta epsilon zeta eta"
    session = _make_session()
    project, version = _create_document_version(session, text=text)
    _create_chunks(session, project=project, version=version)
    provider = FakeDenseEmbeddingProvider()

    result = DenseEmbeddingPipeline(session, provider=provider).embed_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    session.commit()

    chunks = _chunks(session, project=project, version=version)

    assert result.embedded_chunk_count == 2
    assert result.reused_chunk_count == 0
    assert provider.inputs == [
        "Intro section explains the pipeline.\n\nAlpha beta gamma",
        "Delta epsilon zeta eta",
    ]
    assert all(chunk.embedding is not None for chunk in chunks)
    assert all(len(chunk.embedding) == 1024 for chunk in chunks if chunk.embedding)
    assert chunks[0].embedding_metadata == {
        "embedding_dimensions": 1024,
        "embedding_input_hash": chunks[0].embedding_metadata["embedding_input_hash"],
        "embedding_input_kind": "contextual_summary_plus_chunk_text",
        "embedding_index_fingerprint": chunks[0].embedding_metadata[
            "embedding_index_fingerprint"
        ],
        "embedding_metadata_version": "dense_embedding_v1",
        "embedding_model": "fake-embedding-v1",
        "embedding_provider": "fake",
        "lexical_input_hash": chunks[0].embedding_metadata["lexical_input_hash"],
    }
    assert chunks[0].embedding_metadata["embedding_input_hash"].startswith("sha256:")
    assert chunks[0].embedding_metadata["embedding_index_fingerprint"].startswith(
        "sha256:"
    )
    assert chunks[1].embedding_metadata["embedding_input_kind"] == "chunk_text"


def test_embed_document_version_is_idempotent_for_same_provider_and_input() -> None:
    text = "Alpha beta gamma\n\nDelta epsilon zeta eta"
    session = _make_session()
    project, version = _create_document_version(session, text=text)
    _create_chunks(session, project=project, version=version)
    provider = FakeDenseEmbeddingProvider()
    pipeline = DenseEmbeddingPipeline(session, provider=provider)

    first = pipeline.embed_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    second = pipeline.embed_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    session.commit()

    assert first.embedded_chunk_count == 2
    assert second.embedded_chunk_count == 0
    assert second.reused_chunk_count == 2
    assert len(provider.inputs) == 2


def test_embed_document_version_rejects_wrong_dimension_without_partial_persist() -> (
    None
):
    text = "Alpha beta gamma\n\nDelta epsilon zeta eta"
    session = _make_session()
    project, version = _create_document_version(session, text=text)
    _create_chunks(session, project=project, version=version)
    provider = WrongDimensionProvider()

    with pytest.raises(
        DenseEmbeddingPipelineError,
        match="embedding dimension mismatch",
    ):
        DenseEmbeddingPipeline(
            session,
            provider=provider,
        ).embed_document_version(
            project_id=project.id,
            document_version_id=version.id,
        )

    chunks = _chunks(session, project=project, version=version)

    assert all(chunk.embedding is None for chunk in chunks)
    assert all(chunk.embedding_metadata is None for chunk in chunks)
    assert provider.inputs == []


def test_embed_document_version_rejects_cross_project_version() -> None:
    text = "Alpha beta gamma\n\nDelta epsilon zeta eta"
    session = _make_session()
    _project, version = _create_document_version(session, text=text)
    other_project = ProjectRepository(session).create(name="other")
    provider = FakeDenseEmbeddingProvider()
    session.commit()

    with pytest.raises(
        DenseEmbeddingPipelineError,
        match="document version does not belong to project",
    ):
        DenseEmbeddingPipeline(
            session,
            provider=provider,
        ).embed_document_version(
            project_id=other_project.id,
            document_version_id=version.id,
        )

    assert provider.inputs == []
