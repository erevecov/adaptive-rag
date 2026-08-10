"""Ingestion content guard redacts secrets before document versions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Document,
    DocumentVersion,
    Job,
    JobEvent,
    Source,
    Workspace,
)
from adaptive_rag.db.repositories import (
    JobRepository,
    SourceRepository,
    WorkspaceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.ingestion.pipeline import IngestionPipeline
from adaptive_rag.security.secrets import REDACTION_MARKER


def _session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Workspace.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Job.__table__,
            JobEvent.__table__,
        ],
    )
    return create_session_factory(engine)()


def test_ingest_redacts_secret_in_markdown_before_persist() -> None:
    session = _session()
    workspace = WorkspaceRepository(session).create(name="guard")
    secret = "sk-proj-abcdefghijklmnopqrstuvwxyz012345"
    source = SourceRepository(session).create(
        workspace_id=workspace.id,
        source_type="markdown",
        external_id="leaky.md",
        extra_metadata={
            "content": f"# Notes\n\nAPI key {secret} must not be indexed."
        },
    )
    now = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
    JobRepository(session).create(
        workspace_id=workspace.id,
        job_type="ingest_source",
        payload_json={"source_id": str(source.id)},
        run_after=now,
    )
    session.commit()

    result = IngestionPipeline(session).run_next(
        workspace_id=workspace.id,
        worker_id="guard-worker",
        now=now,
        lease_until=now + timedelta(minutes=5),
    )

    assert result is not None
    assert secret not in result.document_version.normalized_text
    assert REDACTION_MARKER in result.document_version.normalized_text
    assert result.document_version.extraction_metadata["content_guard_redactions"] >= 1
