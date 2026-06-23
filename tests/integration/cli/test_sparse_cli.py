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
    Project,
    Source,
)
from adaptive_rag.db.repositories import (
    ChunkRepository,
    DocumentRepository,
    ProjectRepository,
    SourceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.embeddings import FakeSparseEmbeddingProvider


def test_sparse_command_is_registered() -> None:
    runner = CliRunner()

    root = runner.invoke(app, ["--help"])
    command = runner.invoke(app, ["sparse", "--help"])

    assert root.exit_code == 0
    assert "sparse" in root.stdout
    assert command.exit_code == 0
    assert "backfill" in command.stdout


def test_sparse_backfill_command_embeds_project_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _make_session()
    project, version, chunks = _create_document_version_with_chunks(session)
    provider = FakeSparseEmbeddingProvider()
    _patch_sparse_cli(monkeypatch, session=session, provider=provider)

    result = CliRunner().invoke(
        app,
        [
            "sparse",
            "backfill",
            "--project-id",
            str(project.id),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    rows = session.scalars(select(ChunkSparseEmbedding)).all()
    first_chunk_text = version.normalized_text[
        chunks[0].char_start : chunks[0].char_end
    ]

    assert payload == {
        "project_id": str(project.id),
        "document_version_count": 1,
        "embedded_chunk_count": 2,
        "reused_chunk_count": 0,
    }
    assert len(rows) == 2
    assert provider.document_inputs[0] == (
        f"Generated context for Alpha.\n\n{first_chunk_text}"
    )


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
        ],
    )
    return create_session_factory(engine)()


def _create_document_version_with_chunks(session):
    text = (
        "# Product Guide\n\n"
        "## Intro\n\n"
        "Alpha beta evidence explains onboarding for local users.\n\n"
        "## Details\n\n"
        "Delta evidence covers cited answers."
    )
    project = ProjectRepository(session).create(name="demo")
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="guide.md",
    )
    document = DocumentRepository(session).create_document(
        project_id=project.id,
        source_id=source.id,
        stable_id="guide.md",
    )
    version = DocumentRepository(session).create_version(
        project_id=project.id,
        document_id=document.id,
        version_number=1,
        normalized_text=text,
        content_hash="sha256:test",
        index_fingerprint="ingestion-fp",
    )
    first_start = text.index("Alpha")
    first_end = text.index("\n\n## Details")
    second_start = text.index("Delta")
    chunk_repo = ChunkRepository(session)
    first = chunk_repo.create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=first_start,
        char_end=first_end,
        contextual_summary="Generated context for Alpha.",
    )
    second = chunk_repo.create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=1,
        char_start=second_start,
        char_end=len(text),
    )
    session.commit()
    return project, version, [first, second]


def _patch_sparse_cli(
    monkeypatch: pytest.MonkeyPatch,
    *,
    session,
    provider: FakeSparseEmbeddingProvider,
) -> None:
    @contextmanager
    def override_session_scope() -> Iterator[object]:
        yield session

    monkeypatch.setattr(
        "adaptive_rag.cli.sparse.session_scope",
        override_session_scope,
    )
    monkeypatch.setattr(
        "adaptive_rag.cli.sparse.get_cli_sparse_embedding_provider",
        lambda: provider,
    )
