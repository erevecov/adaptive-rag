"""Knowledge lifecycle: resync, content-hash sync status, dedup report."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag import authoring, ingestion_ops
from adaptive_rag.db.models import Document, DocumentVersion, Job, Source
from adaptive_rag.db.repositories import DocumentRepository, SourceRepository
from adaptive_rag.ingestion_ops import IngestionOpsError


@dataclass(frozen=True, slots=True)
class SourceSyncStatus:
    source_id: UUID
    external_id: str
    source_type: str
    latest_content_hash: str | None
    last_synced_at: str | None
    status: str  # never_synced | synced | stale_unknown


@dataclass(frozen=True, slots=True)
class DedupGroup:
    content_hash: str
    document_version_ids: tuple[UUID, ...]
    source_ids: tuple[UUID, ...]
    count: int


@dataclass(frozen=True, slots=True)
class DedupReport:
    project_id: UUID
    groups: tuple[DedupGroup, ...]
    duplicate_group_count: int
    duplicate_version_count: int


@dataclass(frozen=True, slots=True)
class ResyncResult:
    source_id: UUID
    job: Job


def get_source_sync_status(
    session: Session, *, project_id: UUID, source_id: UUID
) -> SourceSyncStatus:
    source = authoring.get_source(session, project_id=project_id, source_id=source_id)
    version = _latest_version_for_source(session, project_id=project_id, source=source)
    meta = source.extra_metadata or {}
    last_synced = meta.get("last_synced_at")
    if not isinstance(last_synced, str):
        last_synced = None
    if version is None:
        status = "never_synced"
        content_hash = None
    else:
        status = "synced"
        content_hash = version.content_hash
    return SourceSyncStatus(
        source_id=source.id,
        external_id=source.external_id,
        source_type=source.source_type,
        latest_content_hash=content_hash,
        last_synced_at=last_synced,
        status=status,
    )


def list_source_sync_statuses(
    session: Session, *, project_id: UUID
) -> list[SourceSyncStatus]:
    sources = SourceRepository(session).list(project_id=project_id)
    return [
        get_source_sync_status(session, project_id=project_id, source_id=source.id)
        for source in sources
    ]


def resync_source(
    session: Session, *, project_id: UUID, source_id: UUID
) -> ResyncResult:
    """Enqueue public ingest_source job for an existing source (re-index path M40)."""

    try:
        authoring.get_source(session, project_id=project_id, source_id=source_id)
        job = ingestion_ops.enqueue_source_ingestion(
            session, project_id=project_id, source_id=source_id
        )
    except IngestionOpsError as exc:
        raise authoring.AuthoringError(exc.detail, status_code=exc.status_code) from exc
    source = SourceRepository(session).get(project_id=project_id, source_id=source_id)
    assert source is not None
    meta = dict(source.extra_metadata or {})
    meta["last_resync_enqueued_at"] = datetime.now(UTC).isoformat()
    SourceRepository(session).update(
        project_id=project_id,
        source_id=source_id,
        extra_metadata=meta,
    )
    return ResyncResult(source_id=source_id, job=job)


def mark_source_synced(
    session: Session,
    *,
    project_id: UUID,
    source_id: UUID,
    content_hash: str,
) -> None:
    """Record successful ingest content hash on the source (lifecycle watermark)."""

    source = authoring.get_source(session, project_id=project_id, source_id=source_id)
    meta = dict(source.extra_metadata or {})
    meta["last_content_hash"] = content_hash
    meta["last_synced_at"] = datetime.now(UTC).isoformat()
    SourceRepository(session).update(
        project_id=project_id,
        source_id=source_id,
        extra_metadata=meta,
    )


def build_dedup_report(session: Session, *, project_id: UUID) -> DedupReport:
    """Report document versions that share the same content_hash (silent dedup view)."""

    authoring.get_project(session, project_id)
    rows = session.execute(
        select(DocumentVersion, Document)
        .join(Document, Document.id == DocumentVersion.document_id)
        .where(Document.project_id == project_id)
    ).all()
    by_hash: dict[str, list[tuple[DocumentVersion, Document]]] = defaultdict(list)
    for version, document in rows:
        by_hash[version.content_hash].append((version, document))

    groups: list[DedupGroup] = []
    duplicate_versions = 0
    for content_hash, items in sorted(by_hash.items(), key=lambda kv: kv[0]):
        if len(items) < 2:
            continue
        version_ids = tuple(version.id for version, _ in items)
        source_ids = tuple(sorted({document.source_id for _, document in items}))
        groups.append(
            DedupGroup(
                content_hash=content_hash,
                document_version_ids=version_ids,
                source_ids=source_ids,
                count=len(items),
            )
        )
        duplicate_versions += len(items)

    return DedupReport(
        project_id=project_id,
        groups=tuple(groups),
        duplicate_group_count=len(groups),
        duplicate_version_count=duplicate_versions,
    )


def dedup_report_payload(report: DedupReport) -> dict[str, Any]:
    return {
        "project_id": str(report.project_id),
        "duplicate_group_count": report.duplicate_group_count,
        "duplicate_version_count": report.duplicate_version_count,
        "groups": [
            {
                "content_hash": group.content_hash,
                "count": group.count,
                "document_version_ids": [str(i) for i in group.document_version_ids],
                "source_ids": [str(i) for i in group.source_ids],
            }
            for group in report.groups
        ],
    }


def source_sync_status_payload(status: SourceSyncStatus) -> dict[str, Any]:
    return {
        "source_id": str(status.source_id),
        "external_id": status.external_id,
        "source_type": status.source_type,
        "latest_content_hash": status.latest_content_hash,
        "last_synced_at": status.last_synced_at,
        "status": status.status,
    }


def _latest_version_for_source(
    session: Session, *, project_id: UUID, source: Source
) -> DocumentVersion | None:
    from adaptive_rag.db.repositories import DocumentFilters

    documents = DocumentRepository(session).list(
        project_id=project_id,
        filters=DocumentFilters(source_id=source.id),
    )
    if not documents:
        return None
    versions = DocumentRepository(session).list_versions(
        project_id=project_id, document_id=documents[0].id
    )
    return versions[-1] if versions else None
