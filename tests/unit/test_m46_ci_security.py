"""Structural checks that CI runs security scanners (M46)."""

from __future__ import annotations

from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"


def test_ci_workflow_includes_bandit_and_pip_audit() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "bandit" in text
    assert "pip-audit" in text
    assert "bandit -r src" in text
