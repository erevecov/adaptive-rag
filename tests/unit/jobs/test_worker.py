"""General worker event-loop and fencing behavior."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from adaptive_rag.jobs.handlers import build_ingestion_registry
from adaptive_rag.jobs.worker import JobWorker, WorkerRunReport


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


def test_default_registry_exposes_system_pricing_handler() -> None:
    registry = build_ingestion_registry(session_factory=lambda: None)  # type: ignore[arg-type]

    definition = registry.get("provider_model_pricing_sync", 1)

    assert definition.queue_name == "system"
    assert definition.allowed_scopes == frozenset({"system"})
    assert definition.allow_manual_enqueue is True


@pytest.mark.parametrize("max_concurrency", [0, 65])
def test_worker_rejects_unsafe_local_concurrency(max_concurrency: int) -> None:
    with pytest.raises(ValueError, match="max_concurrency"):
        JobWorker(
            session_factory=lambda: None,  # type: ignore[arg-type]
            registry=build_ingestion_registry(
                session_factory=lambda: None  # type: ignore[arg-type]
            ),
            queue_names=("default",),
            max_concurrency=max_concurrency,
        )


def test_worker_batch_respects_local_concurrency() -> None:
    async def scenario() -> None:
        worker = JobWorker(
            session_factory=lambda: None,  # type: ignore[arg-type]
            registry=build_ingestion_registry(
                session_factory=lambda: None  # type: ignore[arg-type]
            ),
            queue_names=("default",),
            max_concurrency=3,
        )
        active = 0
        maximum = 0
        release = asyncio.Event()

        async def run_once() -> WorkerRunReport:
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            await release.wait()
            active -= 1
            return WorkerRunReport(status="idle", worker_id=worker.worker_id)

        worker.run_once = run_once  # type: ignore[method-assign]
        batch = asyncio.create_task(worker._run_batch_once())
        for _index in range(100):
            if maximum == 3:
                break
            await asyncio.sleep(0)
        release.set()
        reports = await batch

        assert maximum == 3
        assert len(reports) == 3

    asyncio.run(scenario())
