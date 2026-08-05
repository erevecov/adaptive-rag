"""M49 MCP tool surface and public-path behavior."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import pytest

from adaptive_rag import authoring, provider_runtime
from adaptive_rag.chat import RetrievalGroundedChatRunner
from adaptive_rag.config.settings import Settings
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Chunk,
    ChunkSparseEmbedding,
    Document,
    DocumentVersion,
    Job,
    JobEvent,
    Project,
    Source,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.embeddings import (
    FakeDenseEmbeddingProvider,
    FakeSparseEmbeddingProvider,
)
from adaptive_rag.mcp_server.server import (
    REQUIRED_TOOL_NAMES,
    _providers,
    ask,
    ingest_text,
    list_projects,
    list_sources,
    search,
    tool_names,
)
from adaptive_rag.provider_runtime import ProviderConfigurationError


def _settings(**overrides: Any) -> Settings:
    return Settings(_env_file=None, **overrides)


def _install_memory_session(monkeypatch: Any) -> None:
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
            ChunkSparseEmbedding.__table__,
            Job.__table__,
            JobEvent.__table__,
        ],
    )
    factory = create_session_factory(engine)

    class _Scope:
        def __enter__(self) -> Any:
            self.session = factory()
            return self.session

        def __exit__(self, *args: object) -> None:
            self.session.close()

    monkeypatch.setattr(
        "adaptive_rag.mcp_server.server.session_scope",
        lambda: _Scope(),
    )


def test_tool_names_cover_required_surface() -> None:
    assert set(tool_names()) == set(REQUIRED_TOOL_NAMES)


def test_mcp_cli_module_exports_main() -> None:
    from adaptive_rag.mcp_server import main

    assert callable(main)


def test_cli_registers_mcp_command() -> None:
    source = open("src/adaptive_rag/cli/app.py", encoding="utf-8").read()
    assert 'name="mcp"' in source
    assert "mcp_cmd" in source


def test_providers_use_fake_only_when_settings_request_fake(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        provider_runtime,
        "get_settings",
        lambda: _settings(provider_runtime_mode="fake"),
    )
    dense, sparse, runner = _providers()
    assert isinstance(dense, FakeDenseEmbeddingProvider)
    assert isinstance(sparse, FakeSparseEmbeddingProvider)
    assert isinstance(runner, RetrievalGroundedChatRunner)


def test_providers_raise_when_live_config_broken(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        provider_runtime,
        "get_settings",
        lambda: _settings(
            provider_runtime_mode="live",
            embedding_provider="qwen",
            sparse_embedding_provider="qwen",
            sparse_embedding_model="text-embedding-v4",
            chat_provider="qwen",
            chat_model="qwen-plus",
        ),
    )
    with pytest.raises(
        ProviderConfigurationError,
        match="ADAPTIVE_RAG_QWEN_API_KEY is required",
    ):
        _providers()


def test_search_and_ask_return_structured_error_when_live_misconfigured(
    monkeypatch: Any,
) -> None:
    _install_memory_session(monkeypatch)
    monkeypatch.setattr(
        provider_runtime,
        "get_settings",
        lambda: _settings(
            provider_runtime_mode="live",
            embedding_provider="qwen",
            sparse_embedding_provider="qwen",
            sparse_embedding_model="text-embedding-v4",
            chat_provider="qwen",
            chat_model="qwen-plus",
        ),
    )
    project_id = "00000000-0000-0000-0000-000000000001"
    search_payload = json.loads(search(project_id, "hello", limit=1))
    ask_payload = json.loads(ask(project_id, "hello?"))
    assert search_payload["error"] == "provider_configuration_error"
    assert "ADAPTIVE_RAG_QWEN_API_KEY" in search_payload["message"]
    assert ask_payload["error"] == "provider_configuration_error"
    assert "ADAPTIVE_RAG_QWEN_API_KEY" in ask_payload["message"]


def test_list_projects_and_ingest_text_public_path(monkeypatch: Any) -> None:
    _install_memory_session(monkeypatch)
    monkeypatch.setattr(
        provider_runtime,
        "get_settings",
        lambda: _settings(provider_runtime_mode="fake"),
    )
    assert json.loads(list_projects())["items"] == []

    from adaptive_rag.mcp_server import server as server_mod

    with server_mod.session_scope() as session:
        project = authoring.create_project(session, name="MCP Demo")
        session.commit()
        project_id = str(project.id)

    items = json.loads(list_projects())["items"]
    assert any(item["id"] == project_id for item in items)

    ingest = json.loads(
        ingest_text(
            project_id=project_id,
            external_id="mcp-notes.md",
            content="# MCP\n\nHello from MCP ingest_text.",
        )
    )
    assert ingest["job_type"] == "ingest_source"
    assert UUID(ingest["job_id"])
    assert ingest["source"]["external_id"] == "mcp-notes.md"

    sources = json.loads(list_sources(project_id))["items"]
    assert len(sources) == 1

    search_payload = json.loads(search(project_id, "Hello", limit=3))
    assert "results" in search_payload
    ask_payload = json.loads(ask(project_id, "What is MCP?"))
    assert "answer" in ask_payload
    assert "citation_count" in ask_payload


def test_search_clamps_limit_to_chat_retrieval_max(monkeypatch: Any) -> None:
    from adaptive_rag.db.models import CHAT_RETRIEVAL_MAX_LIMIT
    from adaptive_rag.mcp_server import server as mcp_server

    _install_memory_session(monkeypatch)
    monkeypatch.setattr(
        mcp_server,
        "_providers",
        lambda: (
            FakeDenseEmbeddingProvider(),
            FakeSparseEmbeddingProvider(),
            object(),
        ),
    )
    captured: dict[str, Any] = {}

    class _CaptureService:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def search(self, request: Any) -> list[Any]:
            captured["limit"] = request.limit
            return []

    monkeypatch.setattr(mcp_server, "RetrievalService", _CaptureService)
    payload = json.loads(
        search(
            "00000000-0000-0000-0000-000000000001",
            "hello",
            limit=CHAT_RETRIEVAL_MAX_LIMIT + 100,
        )
    )
    assert "error" not in payload
    assert captured["limit"] == CHAT_RETRIEVAL_MAX_LIMIT
