"""Structural checks for M44 CI, compose, and deferred defaults."""

from __future__ import annotations

from pathlib import Path

from adaptive_rag.v1_quality_gate import DEFERRED_DEFAULTS

ROOT = Path(__file__).resolve().parents[2]


def test_github_actions_ci_workflow_encodes_required_gates() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "ruff check" in workflow
    assert "mypy src" in workflow
    assert "pytest" in workflow
    assert "pnpm test" in workflow
    assert "pnpm typecheck" in workflow
    assert "pnpm lint" in workflow
    assert "pnpm build" in workflow
    assert "openspec" in workflow.lower()


def test_compose_includes_frontend_and_migration_docs() -> None:
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert "frontend:" in compose
    assert "alembic upgrade head" in compose
    assert (ROOT / "frontend" / "Dockerfile").is_file()
    assert (ROOT / "frontend" / "nginx.conf").is_file()


def test_compose_frontend_uses_build_time_api_base_var() -> None:
    # The frontend reads VITE_ADAPTIVE_RAG_API_BASE_URL (frontend/.env.example)
    # and Vite only inlines VITE_* vars at build time, so the compose service
    # must pass it as a build arg, not as runtime container environment.
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert "VITE_ADAPTIVE_RAG_API_BASE_URL" in compose
    assert "VITE_API_BASE_URL" not in compose
    assert "environment:" not in compose.split("frontend:", 1)[1].split("worker:", 1)[0]
    dockerfile = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    assert "ARG VITE_ADAPTIVE_RAG_API_BASE_URL" in dockerfile


def test_deferred_defaults_no_longer_list_auth_multi_user() -> None:
    assert "auth_multi_user" not in DEFERRED_DEFAULTS
    assert "pdf_office_ingestion" in DEFERRED_DEFAULTS
