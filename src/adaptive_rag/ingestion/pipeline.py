"""Pipeline inicial de ingestion para convertir sources en document versions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

import trafilatura
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Document, DocumentVersion, Job, Source
from adaptive_rag.db.repositories import (
    DocumentFilters,
    DocumentRepository,
    JobRepository,
    SourceRepository,
)
from adaptive_rag.ingestion.url_fetch_policy import (
    FetchResult,
    URLFetcher,
    URLFetchPolicyError,
)

INGEST_SOURCE_JOB_TYPE = "ingest_source"
TEXT_SOURCE_TYPES = frozenset({"markdown", "text", "txt"})
HTML_SOURCE_CONTENT_TYPES = frozenset({"application/xhtml+xml", "text/html"})


class IngestionPipelineError(ValueError):
    """Error no retryable de ingestion."""


class URLContentFetcher(Protocol):
    def fetch(self, url: str) -> FetchResult:
        """Descarga una URL ya validada por policy."""


class HTMLExtractor(Protocol):
    def extract(self, *, html: str, url: str) -> ParsedDocument:
        """Extrae texto principal y metadata desde HTML descargado."""


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    normalized_text: str
    parser_metadata: Mapping[str, Any]
    extraction_metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class IngestionRunResult:
    job: Job
    source: Source
    document: Document
    document_version: DocumentVersion
    created_document_version: bool


class BasicTextParser:
    """Parser determinista para fuentes Markdown/TXT inline."""

    parser_version = "basic_text_v1"

    def parse(self, *, content: str, source_type: str) -> ParsedDocument:
        return ParsedDocument(
            normalized_text=normalize_text(content),
            parser_metadata={
                "parser": "basic_text",
                "parser_version": self.parser_version,
                "source_type": source_type,
            },
            extraction_metadata={},
        )


class TrafilaturaHTMLExtractor:
    """Wrapper estrecho sobre Trafilatura para HTML ya descargado."""

    def extract(self, *, html: str, url: str) -> ParsedDocument:
        extracted = trafilatura.extract(html, url=url)
        if not isinstance(extracted, str) or not extracted.strip():
            raise IngestionPipelineError("HTML extraction produced no text")

        metadata_obj: object = trafilatura.extract_metadata(html)
        return ParsedDocument(
            normalized_text=normalize_text(extracted),
            parser_metadata={
                "parser": "trafilatura",
                "parser_version": str(
                    getattr(trafilatura, "__version__", "unknown")
                ),
            },
            extraction_metadata=_metadata_to_dict(metadata_obj),
        )


class IngestionPipeline:
    """Worker-facing pipeline para procesar jobs `ingest_source`."""

    def __init__(
        self,
        session: Session,
        *,
        url_fetcher: URLContentFetcher | None = None,
        html_extractor: HTMLExtractor | None = None,
        text_parser: BasicTextParser | None = None,
    ) -> None:
        self._session = session
        self._source_repo = SourceRepository(session)
        self._document_repo = DocumentRepository(session)
        self._job_repo = JobRepository(session)
        self._url_fetcher = url_fetcher or URLFetcher()
        self._html_extractor = html_extractor or TrafilaturaHTMLExtractor()
        self._text_parser = text_parser or BasicTextParser()

    def run_next(
        self,
        *,
        project_id: UUID,
        worker_id: str,
        now: datetime,
        lease_until: datetime,
    ) -> IngestionRunResult | None:
        job = self._job_repo.lease_next(
            project_id=project_id,
            worker_id=worker_id,
            now=now,
            lease_until=lease_until,
            job_type=INGEST_SOURCE_JOB_TYPE,
        )
        if job is None:
            return None

        try:
            result = self._process_job(project_id=project_id, job=job)
        except (IngestionPipelineError, URLFetchPolicyError) as exc:
            self._job_repo.block(project_id=project_id, job_id=job.id, reason=str(exc))
            return None

        self._job_repo.complete(project_id=project_id, job_id=job.id)
        return result

    def _process_job(self, *, project_id: UUID, job: Job) -> IngestionRunResult:
        source_id = _source_id_from_payload(job.payload_json)
        source = self._source_repo.get(project_id=project_id, source_id=source_id)
        if source is None:
            raise IngestionPipelineError("source does not belong to project")

        parsed = self._parse_source(source)
        content_hash = _sha256_text(parsed.normalized_text)
        parser_metadata = dict(parsed.parser_metadata)
        extraction_metadata = _source_extraction_metadata(source) | dict(
            parsed.extraction_metadata
        )
        index_fingerprint = _index_fingerprint(
            content_hash=content_hash,
            parser_metadata=parser_metadata,
        )
        document = self._get_or_create_document(project_id=project_id, source=source)
        existing_versions = self._document_repo.list_versions(
            project_id=project_id,
            document_id=document.id,
        )
        latest = existing_versions[-1] if existing_versions else None

        if (
            latest is not None
            and latest.content_hash == content_hash
            and latest.index_fingerprint == index_fingerprint
        ):
            return IngestionRunResult(
                job=job,
                source=source,
                document=document,
                document_version=latest,
                created_document_version=False,
            )

        next_version = 1 if latest is None else latest.version_number + 1
        document_version = self._document_repo.create_version(
            project_id=project_id,
            document_id=document.id,
            version_number=next_version,
            normalized_text=parsed.normalized_text,
            content_hash=content_hash,
            index_fingerprint=index_fingerprint,
            parser_metadata=parser_metadata,
            extraction_metadata=extraction_metadata,
        )
        return IngestionRunResult(
            job=job,
            source=source,
            document=document,
            document_version=document_version,
            created_document_version=True,
        )

    def _parse_source(self, source: Source) -> ParsedDocument:
        if source.source_type == "url":
            fetched = self._url_fetcher.fetch(source.external_id)
            content_type = _base_content_type(fetched.content_type)
            if content_type not in HTML_SOURCE_CONTENT_TYPES:
                raise IngestionPipelineError(
                    f"URL source content type is not HTML: {content_type}"
                )
            html = fetched.content.decode("utf-8", errors="replace")
            return self._html_extractor.extract(html=html, url=fetched.final_url)

        if source.source_type in TEXT_SOURCE_TYPES:
            return self._text_parser.parse(
                content=_inline_text_content(source),
                source_type=source.source_type,
            )

        raise IngestionPipelineError(f"Unsupported source_type: {source.source_type}")

    def _get_or_create_document(self, *, project_id: UUID, source: Source) -> Document:
        documents = self._document_repo.list(
            project_id=project_id,
            filters=DocumentFilters(source_id=source.id, stable_id=source.external_id),
        )
        if documents:
            return documents[0]
        return self._document_repo.create_document(
            project_id=project_id,
            source_id=source.id,
            stable_id=source.external_id,
        )


def normalize_text(content: str) -> str:
    """Normaliza line endings y whitespace exterior sin cambiar el cuerpo."""

    return content.replace("\r\n", "\n").replace("\r", "\n").strip()


def _source_id_from_payload(payload: Mapping[str, Any] | None) -> UUID:
    if payload is None:
        raise IngestionPipelineError("ingest_source job payload is required")

    raw_source_id = payload.get("source_id")
    if not isinstance(raw_source_id, str):
        raise IngestionPipelineError("ingest_source job requires string source_id")

    try:
        return UUID(raw_source_id)
    except ValueError as exc:
        raise IngestionPipelineError("ingest_source job source_id is invalid") from exc


def _inline_text_content(source: Source) -> str:
    metadata = source.extra_metadata or {}
    content = metadata.get("content")
    if not isinstance(content, str):
        raise IngestionPipelineError(
            f"{source.source_type} source requires extra_metadata.content"
        )
    return content


def _base_content_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def _sha256_text(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _index_fingerprint(
    *,
    content_hash: str,
    parser_metadata: Mapping[str, Any],
) -> str:
    payload = {
        "content_hash": content_hash,
        "parser_metadata": dict(parser_metadata),
    }
    return _sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _source_extraction_metadata(source: Source) -> dict[str, Any]:
    return {
        "source_external_id": source.external_id,
        "source_type": source.source_type,
    }


def _metadata_to_dict(metadata_obj: object) -> dict[str, Any]:
    if metadata_obj is None:
        return {}

    metadata: dict[str, Any] = {}
    for key in ("title", "author", "date", "description", "sitename", "hostname"):
        if isinstance(metadata_obj, Mapping):
            value = metadata_obj.get(key)
        else:
            value = getattr(metadata_obj, key, None)
        if value not in (None, ""):
            metadata[key] = value
    return metadata
