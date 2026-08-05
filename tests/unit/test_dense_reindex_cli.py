"""M50 dense reindex CLI helpers and force re-embed."""

from __future__ import annotations

from adaptive_rag import authoring
from adaptive_rag.cli.dense import list_project_document_version_ids
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Chunk, Document, DocumentVersion, Project, Source
from adaptive_rag.db.repositories import ChunkRepository, DocumentRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.embeddings import DenseEmbeddingPipeline, FakeDenseEmbeddingProvider


def _session():
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


def _seed_version_with_chunk(session, *, text: str = "chunk text for dense reindex"):
    project = authoring.create_project(session, name="Reindex")
    source = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id="r.md",
        extra_metadata={"content": text},
    )
    doc_repo = DocumentRepository(session)
    document = doc_repo.create_document(
        project_id=project.id,
        source_id=source.id,
        stable_id=source.external_id,
    )
    version = doc_repo.create_version(
        project_id=project.id,
        document_id=document.id,
        version_number=1,
        normalized_text=text,
        content_hash="sha256:test",
        index_fingerprint="sha256:fp",
        parser_metadata={"parser": "basic_text"},
        extraction_metadata={},
    )
    ChunkRepository(session).create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=0,
        char_end=len(text),
        token_count=4,
        chunker_metadata={"chunker_version": "test"},
    )
    session.commit()
    return project, version


def test_list_versions_and_reindex_embeds_chunks() -> None:
    session = _session()
    project, version = _seed_version_with_chunk(session)

    ids = list_project_document_version_ids(session, project_id=project.id)
    assert ids == [version.id]

    result = DenseEmbeddingPipeline(
        session, provider=FakeDenseEmbeddingProvider()
    ).embed_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    assert result.embedded_chunk_count == 1
    assert result.reused_chunk_count == 0

    reused = DenseEmbeddingPipeline(
        session, provider=FakeDenseEmbeddingProvider()
    ).embed_document_version(
        project_id=project.id,
        document_version_id=version.id,
    )
    assert reused.embedded_chunk_count == 0
    assert reused.reused_chunk_count == 1

    forced = DenseEmbeddingPipeline(
        session, provider=FakeDenseEmbeddingProvider()
    ).embed_document_version(
        project_id=project.id,
        document_version_id=version.id,
        force=True,
    )
    assert forced.embedded_chunk_count == 1


def test_cli_module_registers_reindex_command() -> None:
    source = open("src/adaptive_rag/cli/app.py", encoding="utf-8").read()
    assert 'name="dense"' in source
    dense = open("src/adaptive_rag/cli/dense.py", encoding="utf-8").read()
    assert "def reindex" in dense
    assert "watermark" in dense
