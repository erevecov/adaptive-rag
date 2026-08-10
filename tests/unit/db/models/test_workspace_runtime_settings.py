"""Tests for workspace-scoped runtime override persistence models."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    ProviderConnection,
    Workspace,
    WorkspaceChatModel,
    WorkspaceRuntimeSlotOverride,
)
from adaptive_rag.db.repositories import WorkspaceRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Workspace.__table__,
            ProviderConnection.__table__,
            WorkspaceRuntimeSlotOverride.__table__,
            WorkspaceChatModel.__table__,
        ],
    )
    return create_session_factory(engine)()


def _add_workspace_and_connection(session) -> Workspace:
    workspace = WorkspaceRepository(session).create(name="demo")
    session.add(
        ProviderConnection(
            connection_id="qwen-hosted",
            provider="qwen",
            connection_type="hosted",
            capabilities_json=["chat", "rerank"],
        )
    )
    session.flush()
    return workspace


def test_workspace_runtime_slot_override_persists_workspace_model_selection() -> None:
    session = _make_session()
    workspace = _add_workspace_and_connection(session)
    override = WorkspaceRuntimeSlotOverride(
        workspace_id=workspace.id,
        slot="rerank",
        connection_id="qwen-hosted",
        model_id="qwen3-rerank",
        parameters_json={"top_n": 8},
    )

    session.add(override)
    session.commit()
    session.expunge_all()

    fetched = session.get(WorkspaceRuntimeSlotOverride, (workspace.id, "rerank"))

    assert fetched is not None
    assert fetched.connection_id == "qwen-hosted"
    assert fetched.model_id == "qwen3-rerank"
    assert fetched.parameters_json == {"top_n": 8}


def test_workspace_runtime_slot_override_rejects_unknown_slot() -> None:
    session = _make_session()
    workspace = _add_workspace_and_connection(session)
    override = WorkspaceRuntimeSlotOverride(
        workspace_id=workspace.id,
        slot="voice",
        connection_id="qwen-hosted",
        model_id="qwen-voice",
    )

    try:
        session.add(override)
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for unsupported runtime slot")


def test_workspace_chat_model_has_workspace_scoped_composite_identity() -> None:
    columns = {column.name: column for column in inspect(WorkspaceChatModel).columns}

    assert columns["workspace_id"].primary_key
    assert columns["connection_id"].primary_key
    assert columns["model_id"].primary_key
    assert columns["is_default"].nullable is False
