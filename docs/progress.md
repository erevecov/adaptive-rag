# Progreso de Adaptive RAG

## Milestone activo

M6 Evals.

## Ultimo milestone completado

M5 Chat/tool calling cerrado el 2026-06-19.

## Ultimo slice completado

M6 `m6-evals-plan`: abre el change OpenSpec para definir evaluaciones offline
de retrieval/chat con datasets versionados, runners deterministas, metricas
objetivas y reportes JSON antes de providers live, streaming o persistencia de
conversaciones.

Comandos validados:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate m6-evals-plan --strict
openspec list
openspec validate --specs --strict
git diff --check
```

## Change OpenSpec activo

- `m6-evals-plan`

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
- `openspec/specs/chat-tool-calling/spec.md`

## Siguiente tarea recomendada

- `m6-evals-fixtures-contract`: crear el contrato de datasets/versionado y los
  modelos de resultado antes de runners y CLI. Es la opcion recomendada porque
  las metricas y reportes dependen de una forma estable de declarar casos,
  expected evidence, thresholds y errores de dataset.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
