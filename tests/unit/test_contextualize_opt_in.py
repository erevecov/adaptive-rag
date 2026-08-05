"""M50 contextualization LLM opt-in and A/B compare."""

from __future__ import annotations

from adaptive_rag import authoring
from adaptive_rag.cli.contextualize_cmd import compare_contextualizers
from adaptive_rag.contextualization import (
    ContextualizationPipeline,
    DeterministicContextualizer,
    OptInLlmContextualizer,
)
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Chunk, Document, DocumentVersion, Project, Source
from adaptive_rag.db.repositories import ChunkRepository, DocumentRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


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


def _seed(session, text: str = "# Title\n\nBody chunk for contextualization A/B."):
    project = authoring.create_project(session, name="Ctx")
    source = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id="c.md",
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
        content_hash="sha256:ctx",
        index_fingerprint="sha256:ctxfp",
        parser_metadata={"parser": "basic_text"},
        extraction_metadata={},
    )
    ChunkRepository(session).create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=0,
        char_end=len(text),
        token_count=8,
        chunker_metadata={"chunker_version": "test"},
    )
    session.commit()
    return project, version


def test_opt_in_llm_differs_from_deterministic() -> None:
    session = _session()
    project, version = _seed(session)
    chunks = ChunkRepository(session).list_by_document_version(
        project_id=project.id, document_version_id=version.id
    )
    chunk = chunks[0]
    request_kwargs = dict(
        project_id=project.id,
        document_version_id=version.id,
        force=True,
    )

    det = ContextualizationPipeline(
        session, contextualizer=DeterministicContextualizer()
    ).contextualize_document_version(**request_kwargs)
    llm = ContextualizationPipeline(
        session, contextualizer=OptInLlmContextualizer()
    ).contextualize_document_version(**request_kwargs)

    assert det.generated_summaries[0].summary != llm.generated_summaries[0].summary
    assert "LLM-context" in llm.generated_summaries[0].summary
    assert llm.generated_summaries[0].metadata["contextualizer_provider"] == (
        "llm_opt_in"
    )
    # force regenerated the single chunk both times
    assert det.contextualized_chunk_count == 1
    assert llm.contextualized_chunk_count == 1
    assert chunk.id == det.generated_summaries[0].chunk_id


def test_ab_compare_reports_differences() -> None:
    session = _session()
    project, version = _seed(session)
    report = compare_contextualizers(
        session,
        project_id=project.id,
        document_version_id=version.id,
    )
    assert report["chunk_count"] == 1
    assert report["differing_summary_count"] == 1
    assert report["identical"] is False


def test_cli_registers_contextualize_command() -> None:
    source = open("src/adaptive_rag/cli/app.py", encoding="utf-8").read()
    assert 'name="contextualize"' in source
    body = open("src/adaptive_rag/cli/contextualize_cmd.py", encoding="utf-8").read()
    assert "def reindex" in body
    assert "def ab_compare" in body
