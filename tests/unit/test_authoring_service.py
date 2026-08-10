"""Unit tests for public authoring validation and payload helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from adaptive_rag.authoring import (
    MAX_TEXT_SOURCE_CONTENT_CHARS,
    AuthoringError,
    create_source,
    create_workspace,
    get_source,
    get_workspace,
    list_sources,
    list_workspaces,
    source_payload,
    validate_source_create,
    workspace_payload,
)
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Source, Workspace
from adaptive_rag.db.repositories import SourceFilters
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Workspace.__table__, Source.__table__],
    )
    return create_session_factory(engine)()


def _workspace() -> Workspace:
    workspace = Workspace(
        name="Docs",
        embedding_mode="dense_sparse",
        retrieval_contextualization_enabled=True,
        budget_config_json={"monthly_usd": 5},
    )
    workspace.id = uuid4()
    workspace.created_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    workspace.updated_at = datetime(2024, 1, 2, 12, 0, tzinfo=UTC)
    return workspace


def _source(workspace_id: object | None = None) -> Source:
    source = Source(
        workspace_id=workspace_id or uuid4(),
        source_type="markdown",
        external_id="doc-1",
        tags=["a", "b"],
        extra_metadata={"content": "hi"},
    )
    source.id = uuid4()
    source.created_at = datetime(2024, 3, 1, 9, 30, tzinfo=UTC)
    source.updated_at = datetime(2024, 3, 2, 9, 30, tzinfo=UTC)
    return source


def test_authoring_error_carries_detail_and_status() -> None:
    error = AuthoringError("boom", status_code=418)

    assert error.detail == "boom"
    assert error.status_code == 418
    assert str(error) == "boom"


def test_create_workspace_rejects_unknown_embedding_mode() -> None:
    # Invalid mode fails before any repository/session access.
    with pytest.raises(AuthoringError) as excinfo:
        create_workspace(
            object(),  # type: ignore[arg-type]
            name="Docs",
            embedding_mode="sparse_only",
        )

    assert excinfo.value.status_code == 422
    assert "embedding_mode" in excinfo.value.detail


@pytest.mark.parametrize("source_type", ["markdown", "text", "txt"])
def test_validate_source_create_accepts_text_types_with_content(
    source_type: str,
) -> None:
    validate_source_create(
        source_type=source_type,
        extra_metadata={"content": "some text"},
    )


def test_validate_source_create_accepts_url_without_content() -> None:
    validate_source_create(source_type="url", extra_metadata=None)


def test_validate_source_create_rejects_unsupported_type() -> None:
    with pytest.raises(AuthoringError) as excinfo:
        # pdf/docx are supported post-M45; use a type outside the registry.
        validate_source_create(source_type="rss", extra_metadata=None)

    assert excinfo.value.status_code == 422
    assert "source_type must be one of" in excinfo.value.detail


def test_validate_source_create_requires_metadata_for_text_type() -> None:
    with pytest.raises(AuthoringError) as excinfo:
        validate_source_create(source_type="markdown", extra_metadata=None)

    assert excinfo.value.status_code == 422
    assert "requires extra_metadata.content" in excinfo.value.detail


@pytest.mark.parametrize("content", ["", "   ", None, 123])
def test_validate_source_create_rejects_blank_or_non_string_content(
    content: object,
) -> None:
    with pytest.raises(AuthoringError) as excinfo:
        validate_source_create(
            source_type="text",
            extra_metadata={"content": content},
        )

    assert excinfo.value.status_code == 422


@pytest.mark.parametrize("source_type", ["markdown", "text", "txt"])
def test_validate_source_create_rejects_oversized_text_content(
    source_type: str,
) -> None:
    oversized = "x" * (MAX_TEXT_SOURCE_CONTENT_CHARS + 1)
    with pytest.raises(AuthoringError) as excinfo:
        validate_source_create(
            source_type=source_type,
            extra_metadata={"content": oversized},
        )

    assert excinfo.value.status_code == 422
    assert "exceeds max size" in excinfo.value.detail
    assert str(MAX_TEXT_SOURCE_CONTENT_CHARS) in excinfo.value.detail


def test_validate_source_create_accepts_text_content_at_max_size() -> None:
    validate_source_create(
        source_type="markdown",
        extra_metadata={"content": "y" * MAX_TEXT_SOURCE_CONTENT_CHARS},
    )


def test_workspace_payload_serializes_all_fields() -> None:
    workspace = _workspace()

    payload = workspace_payload(workspace)

    assert payload == {
        "id": str(workspace.id),
        "name": "Docs",
        "embedding_mode": "dense_sparse",
        "retrieval_contextualization_enabled": True,
        "budget_config_json": {"monthly_usd": 5},
        "created_at": "2024-01-01T12:00:00+00:00",
        "updated_at": "2024-01-02T12:00:00+00:00",
    }


def test_source_payload_serializes_all_fields() -> None:
    workspace_id = uuid4()
    source = _source(workspace_id=workspace_id)

    payload = source_payload(source)

    assert payload == {
        "id": str(source.id),
        "workspace_id": str(workspace_id),
        "source_type": "markdown",
        "external_id": "doc-1",
        "tags": ["a", "b"],
        "extra_metadata": {"content": "hi"},
        "created_at": "2024-03-01T09:30:00+00:00",
        "updated_at": "2024-03-02T09:30:00+00:00",
    }


def test_create_and_list_workspaces_round_trips_through_repository() -> None:
    session = _make_session()

    workspace = create_workspace(session, name="Docs", embedding_mode="dense")

    assert workspace.embedding_mode == "dense"
    assert get_workspace(session, workspace.id).id == workspace.id
    assert [p.id for p in list_workspaces(session)] == [workspace.id]


def test_get_workspace_raises_not_found_for_unknown_id() -> None:
    session = _make_session()

    with pytest.raises(AuthoringError) as excinfo:
        get_workspace(session, uuid4())

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "workspace not found"


def test_create_source_persists_and_is_listable_and_gettable() -> None:
    session = _make_session()
    workspace = create_workspace(session, name="Docs")

    source = create_source(
        session,
        workspace_id=workspace.id,
        source_type="markdown",
        external_id="doc-1",
        tags=["guide"],
        extra_metadata={"content": "hello"},
    )

    assert (
        get_source(session, workspace_id=workspace.id, source_id=source.id).id
        == source.id
    )
    listed = list_sources(
        session,
        workspace_id=workspace.id,
        filters=SourceFilters(source_type="markdown"),
    )
    assert [s.id for s in listed] == [source.id]


def test_create_source_rejects_duplicate_identity() -> None:
    session = _make_session()
    workspace = create_workspace(session, name="Docs")
    create_source(
        session,
        workspace_id=workspace.id,
        source_type="url",
        external_id="https://example.test",
    )

    with pytest.raises(AuthoringError) as excinfo:
        create_source(
            session,
            workspace_id=workspace.id,
            source_type="url",
            external_id="https://example.test",
        )

    assert excinfo.value.status_code == 409
    assert excinfo.value.detail == "source already exists"


def test_get_source_raises_not_found_for_unknown_source() -> None:
    session = _make_session()
    workspace = create_workspace(session, name="Docs")

    with pytest.raises(AuthoringError) as excinfo:
        get_source(session, workspace_id=workspace.id, source_id=uuid4())

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "source not found"
