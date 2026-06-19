# Progreso de Adaptive RAG

## Milestone activo

M3 Ingestion y retrieval.

## Ultimo milestone completado

M2 Dominio y persistencia cerrado el 2026-06-18.

## Ultimo slice completado

M3 `m3-retrieval-baseline` implementado dentro del change activo
`m3-ingestion-retrieval-plan`.

Comandos validados:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate m3-ingestion-retrieval-plan --strict
openspec validate --specs --strict
openspec list
git diff --check
```

## Change OpenSpec activo

- `m3-ingestion-retrieval-plan`

## Spec canonica activa

- `openspec/specs/domain-schema/spec.md`
- `openspec/specs/repositories/spec.md`
- `openspec/specs/job-queue/spec.md`
- `openspec/specs/url-fetch-policy/spec.md`

## Siguiente tarea recomendada

- `m3-quality-gate`: validar tests, lint, types, specs y reconciliar el cierre
  del milestone M3 antes de archivar el change activo.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
