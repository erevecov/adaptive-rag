# 2026-06-17 M1 completo y M2 abierto

## Contexto

M1 Foundation fue completado y validado. Los PRs #1 a #5 estan mergeados en `main`.

## Evidencia

El quality gate final paso:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
uv run python -c "from adaptive_rag.api.app import app; print(app.title)"
uv run adaptive-rag health
uv run adaptive-rag version
```

Se observaron los outputs esperados:

```text
7 passed
All checks passed!
Success: no issues found in 13 source files
Adaptive RAG
ok
adaptive-rag 0.1.0
```

## Decision

M2 empieza con el change OpenSpec `m2-domain-schema`.

## Siguiente paso recomendado

Implementar `m2-domain-schema` primero. Es la opcion recomendada porque modelos SQLAlchemy y migraciones Alembic estables son prerequisitos para repositories, jobs, ingestion y retrieval.
