"""Tests for M17 chat observability read models."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import ChatSession, Job, Project, ProviderUsage
from adaptive_rag.db.repositories import ChatObservabilityRepository, ProjectRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            Job.__table__,
            ChatSession.__table__,
            ProviderUsage.__table__,
        ],
    )
    return create_session_factory(engine)()


def _make_project(session, name: str = "demo") -> Project:
    return ProjectRepository(session).create(name=name)


def _add_chat_session(
    session,
    *,
    project_id: UUID,
    status: str,
    created_at: datetime,
    error_message: str | None = None,
) -> ChatSession:
    chat_session = ChatSession(
        project_id=project_id,
        status=status,
        error_message=error_message,
        created_at=created_at,
        updated_at=created_at + timedelta(seconds=1),
    )
    session.add(chat_session)
    session.flush()
    return chat_session


def _add_provider_usage(
    session,
    *,
    project_id: UUID,
    created_at: datetime,
    session_id: UUID | None = None,
    operation: str = "chat",
    provider: str = "qwen",
    model: str = "qwen-plus",
    status: str = "succeeded",
    usage_source: str = "provider_reported",
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    input_count: int | None = None,
    estimated_cost_usd: float | None = None,
    latency_ms: int | None = None,
    error_message: str | None = None,
) -> ProviderUsage:
    usage = ProviderUsage(
        project_id=project_id,
        session_id=session_id,
        operation=operation,
        provider=provider,
        model=model,
        status=status,
        usage_source=usage_source,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        input_count=input_count,
        estimated_cost_usd=estimated_cost_usd,
        currency="USD" if estimated_cost_usd is not None else None,
        latency_ms=latency_ms,
        error_message=error_message,
        created_at=created_at,
    )
    session.add(usage)
    session.flush()
    return usage


def test_summary_aggregates_project_usage_latency_and_errors() -> None:
    session = _make_session()
    project = _make_project(session, "demo")
    other_project = _make_project(session, "other")
    base = datetime(2026, 1, 1, tzinfo=UTC)
    long_error = "runner failed: " + ("x" * 220)

    succeeded = _add_chat_session(
        session,
        project_id=project.id,
        status="succeeded",
        created_at=base + timedelta(minutes=1),
    )
    failed = _add_chat_session(
        session,
        project_id=project.id,
        status="failed",
        created_at=base + timedelta(minutes=2),
        error_message=long_error,
    )
    _add_chat_session(
        session,
        project_id=project.id,
        status="running",
        created_at=base + timedelta(minutes=3),
    )
    _add_chat_session(
        session,
        project_id=other_project.id,
        status="failed",
        created_at=base + timedelta(minutes=4),
        error_message="other project failure",
    )

    _add_provider_usage(
        session,
        project_id=project.id,
        session_id=succeeded.id,
        created_at=base + timedelta(minutes=1, seconds=10),
        input_tokens=100,
        output_tokens=40,
        total_tokens=140,
        input_count=1,
        estimated_cost_usd=0.10,
        latency_ms=100,
    )
    _add_provider_usage(
        session,
        project_id=project.id,
        session_id=failed.id,
        created_at=base + timedelta(minutes=2, seconds=10),
        status="failed",
        usage_source="unavailable",
        estimated_cost_usd=None,
        latency_ms=300,
        error_message=long_error,
    )
    _add_provider_usage(
        session,
        project_id=project.id,
        session_id=succeeded.id,
        created_at=base + timedelta(minutes=1, seconds=20),
        input_tokens=25,
        output_tokens=15,
        total_tokens=40,
        estimated_cost_usd=0.05,
        latency_ms=200,
    )
    _add_provider_usage(
        session,
        project_id=project.id,
        created_at=base + timedelta(minutes=5),
        operation="embedding",
        provider="openai",
        model="text-embedding-3-small",
        input_tokens=1_000,
        input_count=2,
        estimated_cost_usd=0.02,
        latency_ms=None,
    )
    _add_provider_usage(
        session,
        project_id=other_project.id,
        created_at=base + timedelta(minutes=5),
        estimated_cost_usd=9.99,
        latency_ms=1,
    )

    summary = ChatObservabilityRepository(session).get_summary(project_id=project.id)

    assert summary.project_id == project.id
    assert summary.filters.created_at_from is None
    assert summary.filters.created_at_to is None
    assert summary.filters.status is None
    assert summary.sessions.total == 3
    assert summary.sessions.by_status == {
        "running": 1,
        "succeeded": 1,
        "failed": 1,
    }
    assert summary.provider_usage.total_records == 4
    assert summary.provider_usage.total_estimated_cost_usd == pytest.approx(0.17)
    assert summary.provider_usage.missing_cost_count == 1

    groups = {
        (group.operation, group.provider, group.model): group
        for group in summary.provider_usage.groups
    }
    chat_group = groups[("chat", "qwen", "qwen-plus")]
    assert chat_group.record_count == 3
    assert chat_group.estimated_cost_usd == pytest.approx(0.15)
    assert chat_group.input_tokens == 125
    assert chat_group.output_tokens == 55
    assert chat_group.total_tokens == 180
    assert chat_group.input_count == 1
    assert chat_group.latency_ms.count == 3
    assert chat_group.latency_ms.min == 100
    assert chat_group.latency_ms.avg == pytest.approx(200.0)
    assert chat_group.latency_ms.p50 == 200
    assert chat_group.latency_ms.p95 == 300
    assert chat_group.latency_ms.max == 300

    embedding_group = groups[("embedding", "openai", "text-embedding-3-small")]
    assert embedding_group.record_count == 1
    assert embedding_group.output_tokens is None
    assert embedding_group.total_tokens is None
    assert embedding_group.input_count == 2
    assert embedding_group.latency_ms.count == 0
    assert embedding_group.latency_ms.min is None
    assert embedding_group.latency_ms.avg is None
    assert embedding_group.latency_ms.p50 is None
    assert embedding_group.latency_ms.p95 is None
    assert embedding_group.latency_ms.max is None

    assert summary.errors.session_error_count == 1
    assert summary.errors.provider_error_count == 1
    assert summary.errors.top_messages[0].message == long_error[:160]
    assert summary.errors.top_messages[0].count == 2


def test_summary_applies_date_and_status_filters_deterministically() -> None:
    session = _make_session()
    project = _make_project(session)
    base = datetime(2026, 1, 1, tzinfo=UTC)

    failed_in_window = _add_chat_session(
        session,
        project_id=project.id,
        status="failed",
        created_at=base + timedelta(hours=1),
        error_message="window failure",
    )
    succeeded_in_window = _add_chat_session(
        session,
        project_id=project.id,
        status="succeeded",
        created_at=base + timedelta(hours=1, minutes=30),
    )
    failed_before_window = _add_chat_session(
        session,
        project_id=project.id,
        status="failed",
        created_at=base - timedelta(minutes=1),
        error_message="old failure",
    )

    _add_provider_usage(
        session,
        project_id=project.id,
        session_id=failed_in_window.id,
        created_at=base + timedelta(hours=1, seconds=1),
        estimated_cost_usd=0.20,
        latency_ms=20,
    )
    _add_provider_usage(
        session,
        project_id=project.id,
        session_id=succeeded_in_window.id,
        created_at=base + timedelta(hours=1, minutes=30, seconds=1),
        estimated_cost_usd=0.30,
        latency_ms=30,
    )
    _add_provider_usage(
        session,
        project_id=project.id,
        created_at=base + timedelta(hours=1, minutes=10),
        operation="embedding",
        provider="openai",
        model="text-embedding-3-small",
        estimated_cost_usd=0.40,
        latency_ms=40,
    )
    _add_provider_usage(
        session,
        project_id=project.id,
        session_id=failed_before_window.id,
        created_at=base - timedelta(seconds=1),
        estimated_cost_usd=0.50,
        latency_ms=50,
    )

    summary = ChatObservabilityRepository(session).get_summary(
        project_id=project.id,
        created_at_from=base,
        created_at_to=base + timedelta(hours=1, minutes=15),
        status="failed",
    )

    assert summary.filters.created_at_from == base
    assert summary.filters.created_at_to == base + timedelta(hours=1, minutes=15)
    assert summary.filters.status == "failed"
    assert summary.sessions.total == 1
    assert summary.sessions.by_status == {
        "running": 0,
        "succeeded": 0,
        "failed": 1,
    }
    assert summary.provider_usage.total_records == 1
    assert summary.provider_usage.total_estimated_cost_usd == pytest.approx(0.20)
    assert summary.errors.session_error_count == 1
    assert summary.errors.provider_error_count == 0
    assert [message.message for message in summary.errors.top_messages] == [
        "window failure"
    ]

    with pytest.raises(ValueError, match="invalid chat session status"):
        ChatObservabilityRepository(session).get_summary(
            project_id=project.id,
            status="done",
        )
