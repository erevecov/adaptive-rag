# Progreso de Adaptive RAG

## Milestone activo

M5 por planificar: chat/tool calling sobre la superficie de retrieval cerrada.

## Ultimo milestone completado

M4 Superficie de retrieval cerrado el 2026-06-19.

## Ultimo slice completado

M4 `m4-quality-gate`: valido tests, lint, types y specs; archivo
`m4-retrieval-surface-plan` y publico la spec canonica
`openspec/specs/retrieval-surface/spec.md`.

Comandos validados:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec archive m4-retrieval-surface-plan --yes
openspec list
openspec validate --specs --strict
git diff --check
```

## Change OpenSpec activo

- Ninguno.

## Spec canonica activa

- `openspec/specs/domain-schema/spec.md`
- `openspec/specs/repositories/spec.md`
- `openspec/specs/job-queue/spec.md`
- `openspec/specs/url-fetch-policy/spec.md`
- `openspec/specs/ingestion-retrieval-plan/spec.md`
- `openspec/specs/ingestion-pipeline/spec.md`
- `openspec/specs/chunking-baseline/spec.md`
- `openspec/specs/embedding-baseline/spec.md`
- `openspec/specs/retrieval-baseline/spec.md`
- `openspec/specs/retrieval-surface/spec.md`

## Siguiente tarea recomendada

- Abrir un nuevo change OpenSpec para M5 chat/tool calling. Es la opcion
  recomendada porque M4 ya dejo una superficie API/CLI estable y el siguiente
  milestone debe definir como la capa conversacional reutiliza esa logica sin
  duplicar retrieval.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
