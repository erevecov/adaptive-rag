# Progreso de Adaptive RAG

## Milestone activo

M2 Dominio y persistencia.

## Ultimo milestone completado

M1 Foundation cerrado el 2026-06-17.

## Ultimo slice completado

M2 `m2-repositories` implementado y archivado el 2026-06-18.

Comandos validados:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate --specs --strict
```

## Change OpenSpec activo

- Ninguno.

## Spec canonica activa

- `openspec/specs/domain-schema/spec.md`
- `openspec/specs/repositories/spec.md`

## Siguiente tarea recomendada

- `m2-job-queue`: implementar jobs, eventos, retries, estados
  `blocked`/`dead-letter` y leasing de workers sobre el dominio persistente.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
