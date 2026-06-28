"""Tests for project runtime settings inheritance and overrides."""

from __future__ import annotations

from uuid import uuid4

import pytest

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    GlobalChatModel,
    GlobalChatRetrievalSettings,
    Project,
    ProjectChatModel,
    ProjectChatRetrievalSettings,
    ProjectRuntimeSlotOverride,
    ProviderConnection,
    RuntimeSlotDefault,
)
from adaptive_rag.db.repositories import (
    ChatRetrievalSettingsRepository,
    ProjectRepository,
    ProjectRuntimeSettingsRepository,
    ProviderConnectionRepository,
    RuntimeSettingsRepository,
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
            ProjectRuntimeSlotOverride.__table__,
            ProjectChatModel.__table__,
            GlobalChatRetrievalSettings.__table__,
            ProjectChatRetrievalSettings.__table__,
        ],
    )
    return create_session_factory(engine)()


def _add_connection(
    session,
    *,
    connection_id: str,
    provider: str = "qwen",
    connection_type: str = "hosted",
    capabilities: list[str],
    base_url: str | None = None,
) -> None:
    ProviderConnectionRepository(session).upsert_connection(
        connection_id=connection_id,
        provider=provider,
        connection_type=connection_type,
        base_url=base_url,
        capabilities=capabilities,
    )


def test_project_slot_override_shadows_global_and_reset_inherits_again() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    _add_connection(session, connection_id="qwen-hosted", capabilities=["rerank"])
    _add_connection(
        session,
        connection_id="local-rerank",
        provider="local_openai_compatible",
        connection_type="local",
        capabilities=["rerank"],
    )
    global_repo = RuntimeSettingsRepository(session)
    global_repo.upsert_slot_default(
        slot="rerank",
        connection_id="qwen-hosted",
        model_id="qwen3-rerank",
    )
    project_repo = ProjectRuntimeSettingsRepository(session)

    override = project_repo.upsert_slot_override(
        project_id=project.id,
        slot="rerank",
        connection_id="local-rerank",
        model_id="local-reranker",
        parameters={"top_n": 4},
    )
    session.commit()

    effective = project_repo.get_project_runtime_settings(project.id)

    assert override.parameters_json == {"top_n": 4}
    assert effective.slots[0].slot == "rerank"
    assert effective.slots[0].source == "overridden"
    assert effective.slots[0].connection_id == "local-rerank"

    deleted = project_repo.delete_slot_override(project_id=project.id, slot="rerank")
    session.commit()
    inherited = project_repo.get_project_runtime_settings(project.id)

    assert deleted is True
    assert inherited.slots[0].source == "inherited"
    assert inherited.slots[0].connection_id == "qwen-hosted"


def test_project_runtime_settings_reject_missing_project_and_bad_connection() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    _add_connection(session, connection_id="chat-only", capabilities=["chat"])
    repository = ProjectRuntimeSettingsRepository(session)

    with pytest.raises(ValueError, match="project_not_found"):
        repository.upsert_slot_override(
            project_id=uuid4(),
            slot="rerank",
            connection_id="chat-only",
            model_id="qwen3-rerank",
        )

    with pytest.raises(ValueError, match="connection_unavailable"):
        repository.upsert_slot_override(
            project_id=project.id,
            slot="rerank",
            connection_id="chat-only",
            model_id="qwen3-rerank",
        )


def test_project_chat_pool_overrides_global_without_mutating_global_pool() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    _add_connection(session, connection_id="qwen-hosted", capabilities=["chat"])
    _add_connection(
        session,
        connection_id="local-chat",
        provider="local_openai_compatible",
        connection_type="local",
        capabilities=["chat"],
    )
    global_repo = RuntimeSettingsRepository(session)
    global_repo.upsert_chat_model(connection_id="qwen-hosted", model_id="qwen-plus")
    project_repo = ProjectRuntimeSettingsRepository(session)

    inherited = project_repo.get_project_runtime_settings(project.id)

    assert [(model.model_id, model.source) for model in inherited.chat_models] == [
        ("qwen-plus", "inherited")
    ]

    project_repo.upsert_chat_model(
        project_id=project.id,
        connection_id="local-chat",
        model_id="llama3.1:8b",
    )
    project_repo.upsert_chat_model(
        project_id=project.id,
        connection_id="qwen-hosted",
        model_id="qwen-plus",
        make_default=True,
    )
    session.commit()

    overridden = project_repo.get_project_runtime_settings(project.id)
    global_models = global_repo.list_chat_models()

    assert [
        (model.connection_id, model.model_id, model.is_default, model.source)
        for model in overridden.chat_models
    ] == [
        ("qwen-hosted", "qwen-plus", True, "overridden"),
        ("local-chat", "llama3.1:8b", False, "overridden"),
    ]
    global_model_states = [
        (model.connection_id, model.model_id, model.is_default)
        for model in global_models
    ]

    assert global_model_states == [("qwen-hosted", "qwen-plus", True)]


def test_project_chat_pool_rejects_deleting_last_or_default_model() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    _add_connection(session, connection_id="qwen-hosted", capabilities=["chat"])
    _add_connection(
        session,
        connection_id="local-chat",
        provider="local_openai_compatible",
        connection_type="local",
        capabilities=["chat"],
    )
    repository = ProjectRuntimeSettingsRepository(session)
    repository.upsert_chat_model(
        project_id=project.id,
        connection_id="qwen-hosted",
        model_id="qwen-plus",
    )

    with pytest.raises(ValueError, match="cannot_delete_last_chat_model"):
        repository.delete_chat_model(
            project_id=project.id,
            connection_id="qwen-hosted",
            model_id="qwen-plus",
        )

    repository.upsert_chat_model(
        project_id=project.id,
        connection_id="local-chat",
        model_id="llama3.1:8b",
    )

    with pytest.raises(ValueError, match="cannot_delete_default_chat_model"):
        repository.delete_chat_model(
            project_id=project.id,
            connection_id="qwen-hosted",
            model_id="qwen-plus",
        )


def test_project_chat_retrieval_settings_inherit_override_and_reset() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="demo")
    repository = ChatRetrievalSettingsRepository(session)
    repository.upsert_global_settings(
        retrieval_limit=6,
        rerank_enabled=True,
        rerank_candidate_limit=10,
    )

    inherited = repository.get_effective_project_settings(project.id)

    assert inherited.source == "global"
    assert inherited.retrieval_limit == 6
    assert inherited.rerank_enabled is True
    assert inherited.rerank_candidate_limit == 10

    override = repository.upsert_project_settings(
        project_id=project.id,
        retrieval_limit=8,
        rerank_enabled=False,
        rerank_candidate_limit=12,
    )
    session.commit()

    effective = repository.get_effective_project_settings(project.id)

    assert override.retrieval_limit == 8
    assert effective.source == "project"
    assert effective.retrieval_limit == 8
    assert effective.rerank_enabled is False
    assert effective.rerank_candidate_limit == 12

    assert repository.delete_project_settings(project_id=project.id) is True
    session.commit()
    reset = repository.get_effective_project_settings(project.id)

    assert reset.source == "global"
    assert reset.retrieval_limit == 6
