"""M45 public path: PDF/DOCX authoring → worker ingest+index → chat citations."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from sqlalchemy import select

from adaptive_rag import authoring, ingestion_ops
from adaptive_rag.authoring import MAX_BINARY_SOURCE_BYTES, AuthoringError
from adaptive_rag.chat import ChatRequest, ChatService, RetrievalGroundedChatRunner
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Chunk,
    ChunkSparseEmbedding,
    Document,
    DocumentVersion,
    Job,
    JobEvent,
    Project,
    Source,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.embeddings import (
    FakeDenseEmbeddingProvider,
    FakeSparseEmbeddingProvider,
)
from adaptive_rag.ingestion.indexing import INDEX_DOCUMENT_VERSION_JOB_TYPE
from adaptive_rag.ingestion.parsers.registry import DOCX_CONTENT_TYPE
from adaptive_rag.ingestion.pipeline import INGEST_SOURCE_JOB_TYPE
from adaptive_rag.ingestion.url_fetch_policy import URLFetchPolicy
from adaptive_rag.retrieval import RetrievalService

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "m45"


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
            ChunkSparseEmbedding.__table__,
            Job.__table__,
            JobEvent.__table__,
        ],
    )
    return create_session_factory(engine)()


def _run_family(session, *, project_id, dense, sparse):
    return ingestion_ops.run_ingestion_family_until_idle(
        session,
        project_id=project_id,
        worker_id="m45-worker",
        dense_embedding_provider=dense,
        sparse_embedding_provider=sparse,
    )


def test_pdf_source_public_path_to_cited_chat() -> None:
    session = _make_session()
    dense = FakeDenseEmbeddingProvider()
    sparse = FakeSparseEmbeddingProvider()
    pdf_b64 = base64.b64encode((FIXTURES / "sample.pdf").read_bytes()).decode("ascii")

    project = authoring.create_project(session, name="M45 PDF Demo")
    source = authoring.create_source(
        session,
        project_id=project.id,
        source_type="pdf",
        external_id="sample.pdf",
        extra_metadata={"content_base64": pdf_b64, "filename": "sample.pdf"},
    )
    ingestion_ops.enqueue_source_ingestion(
        session, project_id=project.id, source_id=source.id
    )
    reports = _run_family(session, project_id=project.id, dense=dense, sparse=sparse)

    assert len(reports) == 2
    assert reports[0].job_type == INGEST_SOURCE_JOB_TYPE
    assert reports[0].status == "processed"
    assert reports[1].job_type == INDEX_DOCUMENT_VERSION_JOB_TYPE
    assert reports[1].status == "processed"
    assert reports[1].chunk_count is not None and reports[1].chunk_count >= 1

    versions = list(session.scalars(select(DocumentVersion)).all())
    assert any("ALPHA-PDF-442" in version.normalized_text for version in versions)
    chunks = list(session.scalars(select(Chunk)).all())
    assert len(chunks) >= 1
    assert all(chunk.embedding is not None for chunk in chunks)

    chat = ChatService(
        runner=RetrievalGroundedChatRunner(),
        retrieval_service=RetrievalService(
            session,
            provider=FakeDenseEmbeddingProvider(),
            sparse_provider=FakeSparseEmbeddingProvider(),
        ),
    ).respond(
        ChatRequest(
            project_id=project.id,
            message="What is the distinctive PDF phrase ALPHA-PDF-442 about?",
            retrieval_limit=5,
        )
    )
    assert chat.answer
    assert len(chat.citations) >= 1
    citation_blob = " ".join(str(item) for item in chat.citations)
    assert (
        "ALPHA-PDF-442" in citation_blob
        or "ALPHA-PDF-442" in chat.answer
        or "sample.pdf" in citation_blob
        or any(
            getattr(item, "source_external_id", None) == "sample.pdf"
            or (
                isinstance(item, dict)
                and item.get("source_external_id") == "sample.pdf"
            )
            for item in chat.citations
        )
    )


def test_docx_source_public_path_creates_chunks() -> None:
    session = _make_session()
    dense = FakeDenseEmbeddingProvider()
    sparse = FakeSparseEmbeddingProvider()
    docx_b64 = base64.b64encode((FIXTURES / "sample.docx").read_bytes()).decode(
        "ascii"
    )

    project = authoring.create_project(session, name="M45 DOCX Demo")
    source = authoring.create_source(
        session,
        project_id=project.id,
        source_type="docx",
        external_id="sample.docx",
        extra_metadata={"content_base64": docx_b64},
    )
    ingestion_ops.enqueue_source_ingestion(
        session, project_id=project.id, source_id=source.id
    )
    reports = _run_family(session, project_id=project.id, dense=dense, sparse=sparse)

    assert reports[0].status == "processed"
    assert reports[1].status == "processed"
    versions = session.scalars(select(DocumentVersion)).all()
    assert any("ALPHA-DOCX-991" in version.normalized_text for version in versions)
    chunks = session.scalars(select(Chunk)).all()
    assert len(chunks) >= 1


def test_url_docx_content_type_constant_matches_fetch_allowlist() -> None:
    assert DOCX_CONTENT_TYPE in URLFetchPolicy().allowed_content_types


def test_authoring_rejects_oversize_and_invalid_base64() -> None:
    with pytest.raises(AuthoringError, match="content_base64 is invalid"):
        authoring.validate_source_create(
            source_type="pdf",
            extra_metadata={"content_base64": "%%%not-base64%%%"},
        )

    oversized = base64.b64encode(b"x" * (MAX_BINARY_SOURCE_BYTES + 1)).decode("ascii")
    with pytest.raises(AuthoringError, match="max binary size"):
        authoring.validate_source_create(
            source_type="docx",
            extra_metadata={"content_base64": oversized},
        )
