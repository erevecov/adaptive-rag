"""Tests del baseline de chunking semantico Markdown.

El chunker debe crear offsets reproducibles sobre
`document_versions.normalized_text`, sin embeddings ni retrieval.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from adaptive_rag.chunking import (
    ChunkingPipeline,
    ChunkingPipelineError,
    SemanticMarkdownChunker,
    SemanticMarkdownChunkerConfig,
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


class WordTokenEstimator:
    name = "word_estimator"

    def count(self, text: str) -> int:
        return len(text.split())


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


def _make_pipeline(session) -> ChunkingPipeline:
    return ChunkingPipeline(
        session,
        chunker=SemanticMarkdownChunker(
            token_estimator=WordTokenEstimator(),
            config=SemanticMarkdownChunkerConfig(
                target_chunk_tokens=8,
                max_chunk_tokens=10,
                overlap_tokens=0,
            ),
        ),
    )


def _make_overlap_pipeline(session) -> ChunkingPipeline:
    return ChunkingPipeline(
        session,
        chunker=SemanticMarkdownChunker(
            token_estimator=WordTokenEstimator(),
            config=SemanticMarkdownChunkerConfig(
                target_chunk_tokens=4,
                max_chunk_tokens=6,
                overlap_tokens=2,
            ),
        ),
    )


def _reconstruct(chunks: list[Chunk], text: str) -> str:
    return "".join(text[chunk.char_start : chunk.char_end] for chunk in chunks)


def _reconstruct_without_overlap(chunks: list[Chunk], text: str) -> str:
    parts: list[str] = []
    previous_end = 0
    for chunk in chunks:
        start = max(chunk.char_start, previous_end)
        parts.append(text[start : chunk.char_end])
        previous_end = max(previous_end, chunk.char_end)
    return "".join(parts)


def test_chunk_document_version_persists_offsets_section_metadata_and_lineage():
    text = (
        "# Intro\n"
        "\n"
        "Short opening paragraph.\n"
        "\n"
        "## Steps\n"
        "\n"
        "- collect sources\n"
        "- parse documents\n"
        "\n"
        "## Notes\n"
        "\n"
        "Keep offsets stable for citations."
    )
    session = _make_session()
    project, version = _create_document_version(session, text=text)

    result = _make_pipeline(session).chunk_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    session.commit()

    chunks = ChunkRepository(session).list_by_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )

    assert result.created_chunks is True
    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))
    assert _reconstruct(chunks, text) == text
    assert chunks[0].prev_chunk_id is None
    assert chunks[0].next_chunk_id == chunks[1].id
    assert chunks[-1].prev_chunk_id == chunks[-2].id
    assert chunks[-1].next_chunk_id is None
    assert chunks[0].section_metadata == {
        "section_path": ["Intro"],
        "heading": "Intro",
    }
    assert chunks[1].section_metadata == {
        "section_path": ["Intro", "Steps"],
        "heading": "Steps",
    }
    assert chunks[0].chunker_metadata["chunker_version"] == "semantic_markdown_v1"
    assert chunks[0].chunker_metadata["chunker_config_hash"].startswith("sha256:")
    assert chunks[0].embedding is None
    assert chunks[0].contextual_summary is None


def test_chunk_document_version_splits_oversized_block_by_token_fallback():
    text = "one two three four five six seven eight nine ten eleven twelve"
    session = _make_session()
    project, version = _create_document_version(session, text=text)

    result = _make_pipeline(session).chunk_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    session.commit()

    chunks = ChunkRepository(session).list_by_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )

    assert result.created_chunks is True
    assert len(chunks) == 2
    assert [chunk.token_count for chunk in chunks] == [8, 4]
    assert _reconstruct(chunks, text) == text


def test_chunk_document_version_records_explicit_overlap():
    text = "one two three four five six seven eight"
    session = _make_session()
    project, version = _create_document_version(session, text=text)

    result = _make_overlap_pipeline(session).chunk_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    session.commit()

    chunks = ChunkRepository(session).list_by_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )

    assert result.created_chunks is True
    assert len(chunks) == 2
    assert chunks[1].char_start < chunks[0].char_end
    assert _reconstruct_without_overlap(chunks, text) == text
    assert chunks[1].token_count == 6


def test_chunk_document_version_is_idempotent_for_same_chunker_config():
    text = "# Title\n\nsame content"
    session = _make_session()
    project, version = _create_document_version(session, text=text)
    pipeline = _make_pipeline(session)

    first = pipeline.chunk_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    second = pipeline.chunk_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    session.commit()

    chunks = ChunkRepository(session).list_by_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )

    assert first.created_chunks is True
    assert second.created_chunks is False
    assert [chunk.id for chunk in second.chunks] == [chunk.id for chunk in first.chunks]
    assert session.scalar(select(func.count()).select_from(Chunk)) == len(chunks)


def test_chunk_document_version_rejects_cross_project_version():
    text = "# Title\n\nprivate content"
    session = _make_session()
    _project, version = _create_document_version(session, text=text)
    other_project = ProjectRepository(session).create(name="other")
    session.commit()

    with pytest.raises(
        ChunkingPipelineError,
        match="document version does not belong to project",
    ):
        _make_pipeline(session).chunk_document_version(
            project_id=other_project.id,
            document_version_id=version.id,
        )

    assert session.scalar(select(func.count()).select_from(Chunk)) == 0
