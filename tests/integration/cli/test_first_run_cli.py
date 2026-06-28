from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import select
from typer.testing import CliRunner

from adaptive_rag.cli.app import app
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


def test_first_run_command_is_registered() -> None:
    runner = CliRunner()

    root = runner.invoke(app, ["--help"])
    command = runner.invoke(app, ["first-run", "--help"])

    assert root.exit_code == 0
    assert "first-run" in root.stdout
    assert command.exit_code == 0
    assert "smoke" in command.stdout


def test_first_run_smoke_creates_indexed_cited_demo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    _patch_first_run_session_scope(monkeypatch, session=session)

    result = CliRunner().invoke(
        app,
        [
            "first-run",
            "smoke",
            "--project-name",
            "First Run Demo",
            "--source-external-id",
            "first-run.md",
            "--worker-id",
            "first-run-test",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "succeeded"
    assert payload["project"]["name"] == "First Run Demo"
    assert payload["source"]["external_id"] == "first-run.md"
    assert payload["job"]["status"] == "succeeded"
    assert payload["document_version_id"] is not None
    assert payload["chunk_count"] >= 1
    assert payload["contextualized_chunk_count"] == payload["chunk_count"]
    assert payload["reused_contextualized_chunk_count"] == 0
    assert payload["embedded_chunk_count"] == payload["chunk_count"]
    assert payload["citation_count"] >= 1
    assert "Adaptive RAG first run" in payload["answer"]
    assert "adaptive-rag chat ask" in payload["next_commands"][0]

    chunks = session.scalars(select(Chunk)).all()
    assert len(chunks) == payload["chunk_count"]
    assert all(chunk.contextual_summary for chunk in chunks)
    assert all(chunk.embedding is not None for chunk in chunks)


def test_first_run_smoke_uses_custom_content_and_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    _patch_first_run_session_scope(monkeypatch, session=session)

    result = CliRunner().invoke(
        app,
        [
            "first-run",
            "smoke",
            "--project-name",
            "Custom Demo",
            "--source-external-id",
            "custom.md",
            "--content",
            "# Custom\n\nAlpha local evidence proves the onboarding path.",
            "--question",
            "What proves the onboarding path?",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["source"]["external_id"] == "custom.md"
    assert payload["question"] == "What proves the onboarding path?"
    assert payload["contextualized_chunk_count"] == payload["chunk_count"]
    assert payload["reused_contextualized_chunk_count"] == 0
    assert "Alpha local evidence" in payload["answer"]
    assert payload["citation_count"] >= 1


def _make_session():
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
    return create_session_factory(engine)()


def _patch_first_run_session_scope(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session,
) -> None:
    @contextmanager
    def override_session_scope() -> Iterator[object]:
        yield session

    monkeypatch.setattr(
        "adaptive_rag.cli.first_run.session_scope",
        override_session_scope,
    )
