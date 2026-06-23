from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_first_run_runbook_documents_required_local_path() -> None:
    content = (ROOT / "docs" / "first-run.md").read_text(encoding="utf-8")

    assert "uv sync --extra dev" in content
    assert "docker compose up --build postgres" in content
    assert "uv run alembic upgrade head" in content
    assert "uv run adaptive-rag first-run smoke" in content
    assert '"status": "succeeded"' in content
    assert '"citation_count"' in content
    assert "Qwen" in content
    assert "Neo4j" in content
    assert "opt-in" in content


def test_readme_points_new_users_to_first_run_smoke() -> None:
    content = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/first-run.md" in content
    assert "uv run adaptive-rag first-run smoke" in content
    assert "authoring -> ingestion -> indexing -> cited chat" in content
