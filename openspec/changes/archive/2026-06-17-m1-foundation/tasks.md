# Tareas M1 Foundation (archivado)

## Contexto

M1 Foundation se entrego via PRs directos (#1 a #5) sin pasar por el flujo
formal de OpenSpec (proposal/spec/tasks). Este archivo se crea a posteriori con
fines de observacion para conservar el registro de entrega de M1.

No hay proposal, design ni spec delta retroactivos. La fuente de verdad de lo
entregado son los commits y PRs mergeados entre `89f2f4f` y `f8f05b6`.

## Entregado

- [x] 1.1 Scaffold del paquete Python (`src/adaptive_rag`). PR #1.
- [x] 1.2 Settings y logging. PR #2.
- [x] 1.3 Base SQLAlchemy, helpers de sesion DB y foundation de Alembic. PR #3.
- [x] 1.4 App factory de FastAPI y endpoint `/health`. PR #4.
- [x] 1.5 Shell CLI de Typer con `version` y `health`. PR #5.

## Quality gate final

Aprobado el 2026-06-17:

```text
uv sync --extra dev
uv run pytest            # 7 passed
uv run ruff check .      # All checks passed!
uv run mypy src          # Success: no issues found in 13 source files
```
