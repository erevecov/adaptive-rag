"""Unit tests for in-app system scheduler (global maintenance tasks)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import ProviderConnection, ProviderModelCatalog
from adaptive_rag.db.models.system_task import (
    PROVIDER_MODEL_PRICING_SYNC_TASK_ID,
    SystemTaskState,
)
from adaptive_rag.db.repositories import (
    ProviderConnectionRepository,
    ProviderModelCatalogRepository,
)
from adaptive_rag.db.session import create_session_factory
from adaptive_rag.provider_pricing import lookup_qwen_pricing
from adaptive_rag.system_scheduler import (
    DEFAULT_PRICING_INTERVAL_SECONDS,
    SystemTaskDefinition,
    ensure_registered_tasks,
    run_due_system_tasks,
    run_provider_pricing_system_task,
    run_system_task,
)


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            ProviderConnection.__table__,
            ProviderModelCatalog.__table__,
            SystemTaskState.__table__,
        ],
    )
    return create_session_factory(engine)()


def _seed_qwen_catalog(session: Session) -> None:
    connections = ProviderConnectionRepository(session)
    catalog = ProviderModelCatalogRepository(session)
    connections.upsert_connection(
        connection_id="qwen-hosted",
        provider="qwen",
        connection_type="hosted",
        capabilities=["chat", "dense_embedding"],
    )
    catalog.upsert_model(
        connection_id="qwen-hosted",
        model_id="qwen-plus",
        capabilities=["chat"],
        pricing=None,
    )
    catalog.upsert_model(
        connection_id="qwen-hosted",
        model_id="text-embedding-v4",
        capabilities=["dense_embedding"],
        pricing=None,
    )
    session.commit()


def test_run_provider_pricing_system_task_updates_catalog_and_state() -> None:
    session = _make_session()
    _seed_qwen_catalog(session)

    result = run_provider_pricing_system_task(
        session,
        worker_id="test-worker",
        force=True,
    )
    session.commit()

    assert result.status == "ran"
    assert result.report is not None
    assert result.report["updated"] == 2

    plus = session.get(ProviderModelCatalog, ("qwen-hosted", "qwen-plus"))
    assert plus is not None
    assert plus.pricing_json is not None
    assert plus.pricing_json["input_per_million_tokens_usd"] == 0.4

    state = session.get(SystemTaskState, PROVIDER_MODEL_PRICING_SYNC_TASK_ID)
    assert state is not None
    assert state.last_status == "succeeded"
    assert state.last_succeeded_at is not None
    assert state.locked_by is None
    assert state.last_report_json is not None
    assert state.last_report_json["updated"] == 2


def test_scheduler_skips_when_not_due() -> None:
    session = _make_session()
    _seed_qwen_catalog(session)

    first = run_provider_pricing_system_task(
        session, worker_id="w1", force=True
    )
    session.commit()
    assert first.status == "ran"

    second = run_provider_pricing_system_task(
        session, worker_id="w1", force=False
    )
    session.commit()
    assert second.status == "skipped_not_due"

    due_again = run_due_system_tasks(
        session,
        worker_id="w1",
        force=False,
        now=datetime.now(UTC) + timedelta(seconds=DEFAULT_PRICING_INTERVAL_SECONDS + 1),
    )
    session.commit()
    assert len(due_again) == 1
    assert due_again[0].status == "ran"


def test_scheduler_skips_when_lease_held_by_other_worker() -> None:
    session = _make_session()
    _seed_qwen_catalog(session)

    # Hold lease without completing the task.
    from adaptive_rag.db.repositories.system_tasks import SystemTaskRepository

    now = datetime.now(UTC)
    leased = SystemTaskRepository(session).try_lease(
        task_id=PROVIDER_MODEL_PRICING_SYNC_TASK_ID,
        worker_id="holder",
        lease_seconds=600,
        interval_seconds=DEFAULT_PRICING_INTERVAL_SECONDS,
        force=True,
        now=now,
    )
    session.commit()
    assert leased is not None

    blocked = run_provider_pricing_system_task(
        session, worker_id="other", force=True, lease_seconds=600
    )
    session.commit()
    assert blocked.status == "skipped_locked"


def test_dry_run_does_not_touch_system_task_or_catalog() -> None:
    session = _make_session()
    _seed_qwen_catalog(session)

    result = run_provider_pricing_system_task(
        session,
        worker_id="dry",
        force=True,
        dry_run=True,
    )
    session.commit()

    assert result.status == "ran"
    assert result.report is not None
    assert result.report["dry_run"] is True
    assert result.report["updated"] == 2

    plus = session.get(ProviderModelCatalog, ("qwen-hosted", "qwen-plus"))
    assert plus is not None
    assert plus.pricing_json is None
    assert session.get(SystemTaskState, PROVIDER_MODEL_PRICING_SYNC_TASK_ID) is None


def test_failed_handler_marks_failed_and_releases_lease() -> None:
    session = _make_session()

    def boom(_session: Session) -> dict[str, object]:
        raise RuntimeError("boom")

    task = SystemTaskDefinition(
        task_id="test_fail_task",
        interval_seconds=60,
        handler=boom,
    )
    result = run_system_task(
        session,
        task=task,
        worker_id="w-fail",
        force=True,
    )
    session.commit()

    assert result.status == "failed"
    assert result.error == "boom"
    state = session.get(SystemTaskState, "test_fail_task")
    assert state is not None
    assert state.last_status == "failed"
    assert state.last_error == "boom"
    assert state.locked_by is None
    assert state.locked_until is None


def test_ensure_registered_tasks_seeds_pricing_task() -> None:
    session = _make_session()
    rows = ensure_registered_tasks(session)
    session.commit()
    assert any(row.task_id == PROVIDER_MODEL_PRICING_SYNC_TASK_ID for row in rows)
    state = session.get(SystemTaskState, PROVIDER_MODEL_PRICING_SYNC_TASK_ID)
    assert state is not None
    assert state.interval_seconds == DEFAULT_PRICING_INTERVAL_SECONDS


def test_force_after_success_is_idempotent_on_catalog_prices() -> None:
    session = _make_session()
    _seed_qwen_catalog(session)
    run_provider_pricing_system_task(session, worker_id="w1", force=True)
    session.commit()
    expected = lookup_qwen_pricing("qwen-plus")
    again = run_provider_pricing_system_task(session, worker_id="w1", force=True)
    session.commit()
    assert again.status == "ran"
    assert again.report is not None
    # Second force: pricing already current → updated 0, unchanged 2.
    assert again.report["updated"] == 0
    assert again.report["unchanged"] == 2
    plus = session.get(ProviderModelCatalog, ("qwen-hosted", "qwen-plus"))
    assert plus is not None
    assert plus.pricing_json == expected
