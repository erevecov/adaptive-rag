from __future__ import annotations

from pathlib import Path


def test_docker_image_includes_eval_fixtures() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    dockerfile = (repo_root / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (repo_root / ".dockerignore").read_text(encoding="utf-8")

    assert "COPY evals ./evals" in dockerfile
    assert "evals" not in {
        line.strip().rstrip("/")
        for line in dockerignore.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
