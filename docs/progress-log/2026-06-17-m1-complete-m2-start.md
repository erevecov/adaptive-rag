# 2026-06-17 M1 complete and M2 opened

## Context

M1 Foundation was completed and validated. PRs #1 through #5 are merged into `main`.

## Evidence

Final quality gate passed:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
uv run python -c "from adaptive_rag.api.app import app; print(app.title)"
uv run adaptive-rag health
uv run adaptive-rag version
```

Expected outputs were observed:

```text
7 passed
All checks passed!
Success: no issues found in 13 source files
Adaptive RAG
ok
adaptive-rag 0.1.0
```

## Decision

M2 starts with OpenSpec change `m2-domain-schema`.

## Recommended next step

Implement `m2-domain-schema` first. It is recommended because stable SQLAlchemy models and Alembic migrations are prerequisites for repositories, jobs, ingestion and retrieval.

