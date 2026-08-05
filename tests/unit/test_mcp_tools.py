"""M49 MCP tool surface and public-path behavior."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from adaptive_rag import authoring
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
from adaptive_rag.mcp_server.server import (
    REQUIRED_TOOL_NAMES,
    ask,
    ingest_text,
    list_projects,
    list_sources,
    search,
    tool_names,
)


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


def test_list_projects_and_ingest_text_public_path(monkeypatch: Any) -> None:
    _install_memory_session(monkeypatch)
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
