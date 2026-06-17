# OpenSpec workflow

Adaptive RAG usa OpenSpec para cambios de comportamiento y arquitectura.

## Estructura

- `openspec/specs/`: specs canonicas ya aceptadas.
- `openspec/changes/<change-id>/`: cambios activos con `proposal.md`, `design.md`, `tasks.md` y delta specs.
- `openspec/changes/archive/`: cambios completados despues de sincronizar specs.

## Flujo recomendado

1. Crear o actualizar un change en `openspec/changes/<change-id>/`.
2. Revisar `proposal.md`, `design.md`, `tasks.md` y `specs/**/spec.md`.
3. Implementar en una branch `codex/<change-id>-<slice>`.
4. Mergear PRs secuenciales para evitar conflictos.
5. Sincronizar las delta specs hacia `openspec/specs/` cuando el cambio quede cerrado.
6. Archivar el change en `openspec/changes/archive/YYYY-MM-DD-<change-id>/`.

## Reglas anti-conflictos

- Un PR de implementacion debe tocar un area principal: schema, repositories, jobs, fetch policy, API o CLI.
- No abrir dos worktrees que modifiquen simultaneamente `alembic/versions`, los mismos modelos SQLAlchemy o el mismo spec delta.
- `docs/roadmap.md` y `docs/progress.md` se modifican solo en PRs de planificacion o cierre.
- El progreso diario se agrega como archivo nuevo en `docs/progress-log/`; no se edita una entrada antigua salvo correccion factual inmediata.
- Cada PR debe salir de `origin/main` actualizado y pasar `uv run pytest`, `uv run ruff check .` y `uv run mypy src` antes de abrirse.

