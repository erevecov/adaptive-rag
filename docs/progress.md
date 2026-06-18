# Progreso de Adaptive RAG

## Milestone activo

M2 Dominio y persistencia.

## Ultimo milestone completado

M1 Foundation cerrado el 2026-06-17.

## Ultimo slice completado

M2 `m2-domain-schema` mergeado y archivado el 2026-06-18.

Comandos validados:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
uv run python -c "from adaptive_rag.api.app import app; print(app.title)"
uv run adaptive-rag health
uv run adaptive-rag version
```

## Change OpenSpec activo

- Ninguno.

## Spec canonica activa

- `openspec/specs/domain-schema/spec.md`

## Siguiente tarea recomendada

- `m2-repositories`: implementar repositories sobre el schema mergeado,
  manteniendo aislamiento obligatorio por `project_id` y filtros tipados.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Agregar entradas de progreso como archivos nuevos en `docs/progress-log/`.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
