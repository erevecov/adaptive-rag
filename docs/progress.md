# Adaptive RAG Progress

## Active milestone

M2 Domain and persistence.

## Last completed milestone

M1 Foundation closed on 2026-06-17.

Validated commands:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
uv run python -c "from adaptive_rag.api.app import app; print(app.title)"
uv run adaptive-rag health
uv run adaptive-rag version
```

## Active OpenSpec change

- `openspec/changes/m2-domain-schema/`

## Coordination rules

- Use one branch/worktree per task slice.
- Branch from current `origin/main`.
- Do not run parallel implementation branches that touch the same files.
- Prefer small PRs that merge sequentially.
- Add progress entries as new files in `docs/progress-log/`.
- At task completion, recommend the next task and state the recommended option with reasoning.

