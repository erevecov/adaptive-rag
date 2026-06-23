from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_v1_quality_gate_runbook_documents_final_gate() -> None:
    content = (ROOT / "docs" / "v1-quality-gate.md").read_text(encoding="utf-8")

    assert "uv sync --extra dev" in content
    assert "docker compose up --build postgres" in content
    assert "uv run alembic upgrade head" in content
    assert "uv run adaptive-rag v1 quality-gate" in content
    assert '"release_decision": "ready_for_v1_0"' in content
    assert '"criteria"' in content
    assert '"first_run"' in content
    assert "Qwen" in content
    assert "Neo4j" in content
    assert "opt-in" in content
    assert "manual git tag or GitHub release" in content


def test_readme_points_to_v1_quality_gate() -> None:
    content = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/v1-quality-gate.md" in content
    assert "uv run adaptive-rag v1 quality-gate" in content
    assert "ready_for_v1_0" in content
    assert "manual git tag or GitHub release" in content
