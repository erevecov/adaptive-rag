from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_runtime_acceptance_runbook_documents_post_runtime_settings_gate() -> None:
    content = (ROOT / "docs" / "runtime-acceptance.md").read_text(
        encoding="utf-8"
    )

    assert "uv sync --extra dev" in content
    assert "docker compose up --build postgres" in content
    assert "uv run alembic upgrade head" in content
    assert "uv run adaptive-rag acceptance runtime-settings-smoke" in content
    assert '"model_catalog_synced"' in content
    assert '"workspace_runtime_override"' in content
    assert '"effective_runtime_resolution"' in content
    assert '"first_run"' in content
    assert "Qwen" in content
    assert "opt-in" in content


def test_readme_points_to_runtime_acceptance_smoke() -> None:
    content = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/runtime-acceptance.md" in content
    assert "uv run adaptive-rag acceptance runtime-settings-smoke" in content
    assert "provider connections" in content
    assert "model catalog" in content


def test_job_platform_runbook_covers_deployment_recovery_and_retention() -> None:
    content = (
        ROOT / "docs" / "architecture" / "job-platform-runbook.md"
    ).read_text(encoding="utf-8")

    assert "uv run alembic upgrade head" in content
    assert "adaptive-rag jobs worker" in content
    assert "adaptive-rag jobs scheduler" in content
    assert "fenced_write_rejected" in content
    assert "LISTEN/NOTIFY" in content
    assert "--apply" in content
    assert "alembic_version" in content
    assert "docker compose down" in content


def test_readme_points_to_complete_job_platform_runbook() -> None:
    content = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/architecture/job-platform-runbook.md" in content
    assert "adaptive-rag jobs worker" in content
    assert "adaptive-rag jobs retention" in content
