"""Tests for global runtime slot and chat model settings models."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    GlobalChatModel,
    GlobalChatRetrievalSettings,
    Project,
    ProjectChatRetrievalSettings,
    ProviderConnection,
    RuntimeSlotDefault,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            ProviderConnection.__table__,
            RuntimeSlotDefault.__table__,
            GlobalChatModel.__table__,
            GlobalChatRetrievalSettings.__table__,
            ProjectChatRetrievalSettings.__table__,
        ],
    )
    return create_session_factory(engine)()


def _add_connection(session, *, connection_id: str = "qwen-hosted") -> None:
    session.add(
        ProviderConnection(
            connection_id=connection_id,
            provider="qwen",
            connection_type="hosted",
            capabilities_json=["chat", "rerank"],
        )
    )
    session.flush()


def test_runtime_slot_default_persists_fixed_slot_model_and_parameters() -> None:
    session = _make_session()
    _add_connection(session)
    default = RuntimeSlotDefault(
        slot="rerank",
        connection_id="qwen-hosted",
        model_id="qwen3-rerank",
        parameters_json={"top_n": 8},
    )

    session.add(default)
    session.commit()
    session.expunge_all()

    fetched = session.get(RuntimeSlotDefault, "rerank")

    assert fetched is not None
    assert fetched.connection_id == "qwen-hosted"
    assert fetched.model_id == "qwen3-rerank"
    assert fetched.parameters_json == {"top_n": 8}


def test_runtime_slot_default_rejects_unknown_slot() -> None:
    session = _make_session()
    _add_connection(session)
    default = RuntimeSlotDefault(
        slot="voice",
        connection_id="qwen-hosted",
        model_id="qwen-voice",
    )

    try:
        session.add(default)
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for unsupported runtime slot")


def test_global_chat_model_has_composite_identity_and_default_flag() -> None:
    columns = {column.name: column for column in inspect(GlobalChatModel).columns}

    assert columns["connection_id"].primary_key
    assert columns["model_id"].primary_key
    assert columns["is_default"].nullable is False


def test_global_chat_retrieval_settings_persist_defaults_and_limits() -> None:
    session = _make_session()
    settings = GlobalChatRetrievalSettings(
        id=1,
        retrieval_limit=5,
        rerank_enabled=True,
        rerank_candidate_limit=10,
        max_limit=50,
    )

    session.add(settings)
    session.commit()
    session.expunge_all()

    fetched = session.get(GlobalChatRetrievalSettings, 1)

    assert fetched is not None
    assert fetched.retrieval_limit == 5
    assert fetched.rerank_enabled is True
    assert fetched.rerank_candidate_limit == 10
    assert fetched.max_limit == 50


def test_project_chat_retrieval_settings_are_project_scoped() -> None:
    session = _make_session()
    project = Project(name="demo")
    session.add(project)
    session.flush()
    override = ProjectChatRetrievalSettings(
        project_id=project.id,
        retrieval_limit=8,
        rerank_enabled=False,
        rerank_candidate_limit=12,
    )

    session.add(override)
    session.commit()
    session.expunge_all()

    fetched = session.get(ProjectChatRetrievalSettings, project.id)

    assert fetched is not None
    assert fetched.retrieval_limit == 8
    assert fetched.rerank_enabled is False
    assert fetched.rerank_candidate_limit == 12
