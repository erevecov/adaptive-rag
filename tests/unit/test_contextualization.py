"""Tests for generated contextual summaries before dense embedding."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from adaptive_rag.contextualization import (
    ContextualizationPipeline,
    ContextualizationPipelineError,
    DeterministicContextualizer,
)
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Chunk, Document, DocumentVersion, Project, Source
from adaptive_rag.db.repositories import (
    ChunkRepository,
    DocumentRepository,
    ProjectRepository,
    SourceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.embeddings import DenseEmbeddingPipeline, FakeDenseEmbeddingProvider


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


def _create_chunks(
    session,
    *,
    project: Project,
    version: DocumentVersion,
    first_summary: str | None = None,
) -> None:
    text = version.normalized_text
    first_start = text.index("Alpha")
    first_end = text.index("\n\n## Details")
    second_start = text.index("Delta")
    repo = ChunkRepository(session)
    repo.create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=first_start,
        char_end=first_end,
        token_count=6,
        section_metadata={"heading": "Intro", "section_path": ["Intro"]},
        chunker_metadata={"chunker_version": "semantic_markdown_v1"},
        contextual_summary=first_summary,
    )
    repo.create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=1,
        char_start=second_start,
        char_end=len(text),
        token_count=5,
        section_metadata={"heading": "Details", "section_path": ["Details"]},
        chunker_metadata={"chunker_version": "semantic_markdown_v1"},
    )
    session.commit()


def _chunks(session, *, project: Project, version: DocumentVersion) -> list[Chunk]:
    return ChunkRepository(session).list_by_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )


def test_contextualization_pipeline_generates_bounded_summaries() -> None:
    text = (
        "# Product Guide\n\n"
        "## Intro\n\n"
        "Alpha beta evidence explains onboarding for local users.\n\n"
        "## Details\n\n"
        "Delta evidence covers cited answers."
    )
    session = _make_session()
    project, version = _create_document_version(session, text=text)
    _create_chunks(session, project=project, version=version)

    result = ContextualizationPipeline(
        session,
        contextualizer=DeterministicContextualizer(max_summary_chars=180),
    ).contextualize_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    session.commit()

    chunks = _chunks(session, project=project, version=version)

    assert result.contextualized_chunk_count == 2
    assert result.reused_contextualized_chunk_count == 0
    assert result.generated_summaries[0].summary == chunks[0].contextual_summary
    assert chunks[0].contextual_summary == (
        "Document: Product Guide. Section: Intro. "
        "Chunk 1: Alpha beta evidence explains onboarding for local users."
    )
    assert chunks[1].contextual_summary == (
        "Document: Product Guide. Section: Details. "
        "Chunk 2: Delta evidence covers cited answers."
    )
    assert chunks[0].char_start == text.index("Alpha")
    assert text[chunks[0].char_start : chunks[0].char_end].startswith("Alpha beta")


def test_contextualization_pipeline_reuses_existing_summaries() -> None:
    text = (
        "# Product Guide\n\n"
        "## Intro\n\n"
        "Alpha beta evidence explains onboarding for local users.\n\n"
        "## Details\n\n"
        "Delta evidence covers cited answers."
    )
    session = _make_session()
    project, version = _create_document_version(session, text=text)
    _create_chunks(
        session,
        project=project,
        version=version,
        first_summary="Existing generated context.",
    )

    first = ContextualizationPipeline(session).contextualize_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    second = ContextualizationPipeline(session).contextualize_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    session.commit()

    chunks = _chunks(session, project=project, version=version)

    assert first.contextualized_chunk_count == 1
    assert first.reused_contextualized_chunk_count == 1
    assert second.contextualized_chunk_count == 0
    assert second.reused_contextualized_chunk_count == 2
    assert chunks[0].contextual_summary == "Existing generated context."
    assert chunks[1].contextual_summary is not None
    assert session.scalar(select(func.count()).select_from(Chunk)) == 2


def test_generated_context_feeds_dense_embedding_inputs() -> None:
    text = (
        "# Product Guide\n\n"
        "## Intro\n\n"
        "Alpha beta evidence explains onboarding for local users.\n\n"
        "## Details\n\n"
        "Delta evidence covers cited answers."
    )
    session = _make_session()
    project, version = _create_document_version(session, text=text)
    _create_chunks(session, project=project, version=version)
    provider = FakeDenseEmbeddingProvider()

    ContextualizationPipeline(session).contextualize_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    result = DenseEmbeddingPipeline(session, provider=provider).embed_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    session.commit()

    chunks = _chunks(session, project=project, version=version)
    first_chunk_text = text[chunks[0].char_start : chunks[0].char_end]

    assert result.embedded_chunk_count == 2
    assert provider.inputs[0] == (
        f"{chunks[0].contextual_summary}\n\n{first_chunk_text}"
    )
    assert chunks[0].embedding_metadata["embedding_input_kind"] == (
        "contextual_summary_plus_chunk_text"
    )


def test_contextualization_pipeline_rejects_cross_project_version() -> None:
    text = (
        "# Product Guide\n\n"
        "## Intro\n\n"
        "Alpha beta evidence explains onboarding for local users.\n\n"
        "## Details\n\n"
        "Delta evidence covers cited answers."
    )
    session = _make_session()
    _project, version = _create_document_version(session, text=text)
    other_project = ProjectRepository(session).create(name="other")
    session.commit()

    with pytest.raises(
        ContextualizationPipelineError,
        match="document version does not belong to project",
    ):
        ContextualizationPipeline(session).contextualize_document_version(
            project_id=other_project.id,
            document_version_id=version.id,
        )

    assert session.scalar(select(func.count()).select_from(Chunk)) == 0
