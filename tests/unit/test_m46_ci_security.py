"""Structural + executable checks that CI security scanners work (M46)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def test_ci_workflow_includes_bandit_and_pip_audit() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "bandit" in text
    assert "pip-audit" in text
    assert "bandit -r src" in text


def test_bandit_scan_of_src_exits_zero() -> None:
    """Honest gate: bandit must pass on shipped src (not just workflow text)."""

    bandit = shutil.which("bandit")
    if bandit is None:
        cmd = ["uv", "tool", "run", "bandit", "-r", "src", "-q"]
    else:
        cmd = [bandit, "-r", "src", "-q"]
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "bandit reported issues (CI would fail):\n"
        f"{result.stdout}\n{result.stderr}"
    )
