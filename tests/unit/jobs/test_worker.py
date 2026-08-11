"""General worker event-loop and fencing behavior."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from adaptive_rag.jobs.handlers import build_ingestion_registry
from adaptive_rag.jobs.worker import JobWorker


def test_run_once_sync_rejects_an_active_event_loop() -> None:
    worker = JobWorker.__new__(JobWorker)

    async def call_sync() -> None:
        with pytest.raises(RuntimeError, match="active event loop"):
            worker.run_once_sync()

    asyncio.run(call_sync())


def test_ingestion_registry_exposes_typed_versioned_handlers() -> None:
    registry = build_ingestion_registry(session_factory=lambda: None)  # type: ignore[arg-type]
    source_id = uuid4()
    document_version_id = uuid4()

    source_payload = registry.validate_payload(
        "ingest_source", 1, {"source_id": str(source_id)}
    )
    index_payload = registry.validate_payload(
        "index_document_version",
        1,
        {"document_version_id": str(document_version_id)},
    )

    assert source_payload.source_id == source_id
    assert index_payload.document_version_id == document_version_id
    assert registry.get("ingest_source", 1).queue_name == "ingestion"
