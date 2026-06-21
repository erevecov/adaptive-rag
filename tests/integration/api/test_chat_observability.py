"""Tests for the chat observability HTTP surface."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import get_session
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import ChatSession, Job, Project, ProviderUsage
from adaptive_rag.db.repositories import ProjectRepository
from adaptive_rag.db.session import create_session_factory


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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


def _client(*, session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _create_project(session: Session, name: str = "demo") -> Project:
    return ProjectRepository(session).create(name=name)


def _add_chat_session(
    session: Session,
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
    session: Session,
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


def test_chat_observability_summary_endpoint_returns_filtered_project_summary() -> None:
    session = _make_session()
    project = _create_project(session, "demo")
    other_project = _create_project(session, "other")
    base = datetime(2026, 1, 1, tzinfo=UTC)

    failed = _add_chat_session(
        session,
        project_id=project.id,
        status="failed",
        created_at=base + timedelta(hours=1),
        error_message="runner failed",
    )
    succeeded = _add_chat_session(
        session,
        project_id=project.id,
        status="succeeded",
        created_at=base + timedelta(hours=2),
    )
    _add_chat_session(
        session,
        project_id=other_project.id,
        status="failed",
        created_at=base + timedelta(hours=1),
        error_message="other failure",
    )

    _add_provider_usage(
        session,
        project_id=project.id,
        session_id=failed.id,
        created_at=base + timedelta(hours=1, seconds=1),
        status="failed",
        usage_source="unavailable",
        estimated_cost_usd=None,
        latency_ms=100,
        error_message="runner failed",
    )
    _add_provider_usage(
        session,
        project_id=project.id,
        session_id=failed.id,
        created_at=base + timedelta(hours=1, seconds=2),
        input_tokens=10,
        output_tokens=4,
        total_tokens=14,
        input_count=1,
        estimated_cost_usd=0.05,
        latency_ms=300,
    )
    _add_provider_usage(
        session,
        project_id=project.id,
        session_id=succeeded.id,
        created_at=base + timedelta(hours=2, seconds=1),
        estimated_cost_usd=0.40,
        latency_ms=400,
    )
    _add_provider_usage(
        session,
        project_id=other_project.id,
        created_at=base + timedelta(hours=1),
        estimated_cost_usd=9.99,
        latency_ms=999,
    )
    session.commit()
    client = _client(session=session)

    response = client.get(
        f"/projects/{project.id}/chat/observability/summary",
        params={
            "created_at_from": base.isoformat(),
            "created_at_to": (base + timedelta(hours=2)).isoformat(),
            "status": "failed",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == str(project.id)
    assert data["filters"] == {
        "created_at_from": "2026-01-01T00:00:00Z",
        "created_at_to": "2026-01-01T02:00:00Z",
        "status": "failed",
    }
    assert data["sessions"] == {
        "total": 1,
        "by_status": {"running": 0, "succeeded": 0, "failed": 1},
    }
    assert data["provider_usage"]["total_records"] == 2
    assert data["provider_usage"]["total_estimated_cost_usd"] == pytest.approx(0.05)
    assert data["provider_usage"]["missing_cost_count"] == 1
    assert data["provider_usage"]["groups"] == [
        {
            "operation": "chat",
            "provider": "qwen",
            "model": "qwen-plus",
            "record_count": 2,
            "estimated_cost_usd": 0.05,
            "input_tokens": 10,
            "output_tokens": 4,
            "total_tokens": 14,
            "input_count": 1,
            "latency_ms": {
                "count": 2,
                "min": 100,
                "avg": 200.0,
                "p50": 100,
                "p95": 300,
                "max": 300,
            },
        }
    ]
    assert data["errors"] == {
        "session_error_count": 1,
        "provider_error_count": 1,
        "top_messages": [{"message": "runner failed", "count": 2}],
    }


def test_chat_observability_summary_endpoint_maps_invalid_filters_to_422() -> None:
    session = _make_session()
    project = _create_project(session)
    session.commit()
    client = _client(session=session)

    response = client.get(
        f"/projects/{project.id}/chat/observability/summary",
        params={"status": "done"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "invalid chat session status"}
