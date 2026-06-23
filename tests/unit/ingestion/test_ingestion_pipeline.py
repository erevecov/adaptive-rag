"""Tests del primer slice M3 de ingestion.

El pipeline debe convertir jobs `ingest_source` en document versions usando
repositories existentes, sin crear chunks ni llamar providers live.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Chunk,
    Document,
    DocumentVersion,
    Job,
    JobEvent,
    Project,
    Source,
)
from adaptive_rag.db.repositories import (
    DocumentRepository,
    JobRepository,
    ProjectRepository,
    SourceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.ingestion import FetchResult
from adaptive_rag.ingestion.pipeline import (
    IngestionBlockedResult,
    IngestionPipeline,
    ParsedDocument,
)


class FakeURLFetcher:
    def __init__(self, result: FetchResult) -> None:
        self.result = result
        self.requested_urls: list[str] = []

    def fetch(self, url: str) -> FetchResult:
        self.requested_urls.append(url)
        return self.result


class FakeHTMLExtractor:
    def __init__(self, parsed: ParsedDocument) -> None:
        self.parsed = parsed
        self.calls: list[tuple[str, str]] = []

    def extract(self, *, html: str, url: str) -> ParsedDocument:
        self.calls.append((html, url))
        return self.parsed


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
            Job.__table__,
            JobEvent.__table__,
        ],
    )
    return create_session_factory(engine)()


def _run_time() -> datetime:
    return datetime(2026, 6, 18, 22, 0, tzinfo=UTC)


def _enqueue_ingest_job(session, *, project: Project, source: Source) -> Job:
    return JobRepository(session).create(
        project_id=project.id,
        job_type="ingest_source",
        payload_json={"source_id": str(source.id)},
        run_after=_run_time(),
    )


def _event_types(session, *, project: Project, job: Job) -> list[str]:
    return [
        event.event_type
        for event in JobRepository(session).list_events(
            project_id=project.id,
            job_id=job.id,
        )
    ]


def _chunk_count(session) -> int:
    return session.scalar(select(func.count()).select_from(Chunk))


def test_run_next_ingests_markdown_source_into_document_version() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="notes.md",
        extra_metadata={"content": "# Title\r\n\r\nBody"},
    )
    job = _enqueue_ingest_job(session, project=project, source=source)
    session.commit()

    result = IngestionPipeline(session).run_next(
        project_id=project.id,
        worker_id="worker-1",
        now=_run_time(),
        lease_until=_run_time() + timedelta(minutes=10),
    )

    assert result is not None
    assert result.created_document_version is True
    assert result.document_version.normalized_text == "# Title\n\nBody"
    assert result.document_version.version_number == 1
    assert result.document_version.content_hash.startswith("sha256:")
    assert result.document_version.index_fingerprint.startswith("sha256:")
    assert result.document_version.parser_metadata == {
        "parser": "basic_text",
        "parser_version": "basic_text_v1",
        "source_type": "markdown",
    }
    assert result.document_version.extraction_metadata == {
        "source_external_id": "notes.md",
        "source_type": "markdown",
    }
    assert JobRepository(session).get(project_id=project.id, job_id=job.id).status == (
        "succeeded"
    )
    assert _event_types(session, project=project, job=job) == [
        "created",
        "leased",
        "completed",
    ]
    assert _chunk_count(session) == 0


def test_run_next_is_idempotent_for_same_content_and_fingerprint() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="txt",
        external_id="notes.txt",
        extra_metadata={"content": "same content"},
    )
    first_job = _enqueue_ingest_job(session, project=project, source=source)
    session.commit()

    first = IngestionPipeline(session).run_next(
        project_id=project.id,
        worker_id="worker-1",
        now=_run_time(),
        lease_until=_run_time() + timedelta(minutes=10),
    )
    second_job = _enqueue_ingest_job(session, project=project, source=source)
    session.commit()
    second = IngestionPipeline(session).run_next(
        project_id=project.id,
        worker_id="worker-2",
        now=_run_time(),
        lease_until=_run_time() + timedelta(minutes=10),
    )

    versions = DocumentRepository(session).list_versions(
        project_id=project.id,
        document_id=first.document.id,
    )

    assert [version.id for version in versions] == [first.document_version.id]
    assert second.document_version.id == first.document_version.id
    assert second.created_document_version is False
    assert JobRepository(session).get(
        project_id=project.id,
        job_id=first_job.id,
    ).status == "succeeded"
    assert JobRepository(session).get(
        project_id=project.id,
        job_id=second_job.id,
    ).status == "succeeded"


def test_run_next_blocks_job_when_source_belongs_to_another_project() -> None:
    session = _make_session()
    project_a = ProjectRepository(session).create(name="a")
    project_b = ProjectRepository(session).create(name="b")
    source_a = SourceRepository(session).create(
        project_id=project_a.id,
        source_type="txt",
        external_id="a.txt",
        extra_metadata={"content": "private"},
    )
    job = JobRepository(session).create(
        project_id=project_b.id,
        job_type="ingest_source",
        payload_json={"source_id": str(source_a.id)},
        run_after=_run_time(),
    )
    session.commit()

    result = IngestionPipeline(session).run_next(
        project_id=project_b.id,
        worker_id="worker-1",
        now=_run_time(),
        lease_until=_run_time() + timedelta(minutes=10),
    )

    documents = DocumentRepository(session).list(project_id=project_b.id)

    assert isinstance(result, IngestionBlockedResult)
    assert result.job.id == job.id
    assert result.error_message == "source does not belong to project"
    assert documents == []
    blocked_job = JobRepository(session).get(project_id=project_b.id, job_id=job.id)

    assert blocked_job.status == "blocked"
    assert _event_types(session, project=project_b, job=job) == [
        "created",
        "leased",
        "blocked",
    ]


def test_run_next_fetches_url_and_uses_html_extractor() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="url",
        external_id="https://example.com/article",
    )
    _enqueue_ingest_job(session, project=project, source=source)
    fetcher = FakeURLFetcher(
        FetchResult(
            final_url="https://example.com/article",
            status_code=200,
            content_type="text/html",
            content=b"<html><body><article>Hello</article></body></html>",
        )
    )
    extractor = FakeHTMLExtractor(
        ParsedDocument(
            normalized_text="Hello",
            parser_metadata={
                "parser": "fake_html",
                "parser_version": "fake_html_v1",
            },
            extraction_metadata={"title": "Example"},
        )
    )
    session.commit()

    result = IngestionPipeline(
        session,
        url_fetcher=fetcher,
        html_extractor=extractor,
    ).run_next(
        project_id=project.id,
        worker_id="worker-1",
        now=_run_time(),
        lease_until=_run_time() + timedelta(minutes=10),
    )

    assert result is not None
    assert fetcher.requested_urls == ["https://example.com/article"]
    assert extractor.calls == [
        (
            "<html><body><article>Hello</article></body></html>",
            "https://example.com/article",
        )
    ]
    assert result.document_version.normalized_text == "Hello"
    assert result.document_version.extraction_metadata == {
        "source_external_id": "https://example.com/article",
        "source_type": "url",
        "title": "Example",
    }


def test_run_next_blocks_url_source_when_fetch_result_is_not_html() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="url",
        external_id="https://example.com/file.pdf",
    )
    job = _enqueue_ingest_job(session, project=project, source=source)
    fetcher = FakeURLFetcher(
        FetchResult(
            final_url="https://example.com/file.pdf",
            status_code=200,
            content_type="application/pdf",
            content=b"%PDF-1.7",
        )
    )
    extractor = FakeHTMLExtractor(
        ParsedDocument(
            normalized_text="should not be used",
            parser_metadata={"parser": "fake_html"},
            extraction_metadata={},
        )
    )
    session.commit()

    result = IngestionPipeline(
        session,
        url_fetcher=fetcher,
        html_extractor=extractor,
    ).run_next(
        project_id=project.id,
        worker_id="worker-1",
        now=_run_time(),
        lease_until=_run_time() + timedelta(minutes=10),
    )

    assert isinstance(result, IngestionBlockedResult)
    assert result.job.id == job.id
    assert (
        result.error_message
        == "URL source content type is not HTML: application/pdf"
    )
    assert fetcher.requested_urls == ["https://example.com/file.pdf"]
    assert extractor.calls == []
    assert DocumentRepository(session).list(project_id=project.id) == []
    assert JobRepository(session).get(project_id=project.id, job_id=job.id).status == (
        "blocked"
    )
    assert _event_types(session, project=project, job=job) == [
        "created",
        "leased",
        "blocked",
    ]
