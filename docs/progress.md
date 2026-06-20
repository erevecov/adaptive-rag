# Progreso de Adaptive RAG

## Milestone activo

M11 Retrieval strategy decision.

## Ultimo milestone completado

M10 Retrieval eval datasets y decision gates cerrado el 2026-06-20.

## Ultimo slice completado

M11 `m11-candidate-limit-ab-runner`: agrega un runner interno que reutiliza la
matriz de candidate limits, ejecuta dense baseline una vez y serializa filas
A/B de quality/cost/regressions por limite, incluyendo conteos por `intent` y
`difficulty`.

Comandos validados:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m11-retrieval-strategy-decision --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- `openspec/changes/m11-retrieval-strategy-decision/`

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
- `openspec/specs/evals-baseline/spec.md`
- `openspec/specs/provider-runtime/spec.md`
- `openspec/specs/hosted-evals/spec.md`
- `openspec/specs/retrieval-quality/spec.md`

## Siguiente tarea recomendada

- Despues de mergear `m11-candidate-limit-ab-runner`, decidir si la evidencia
  del reporte A/B justifica `m11-candidate-limit-api-cli-surface`; si no,
  avanzar directo a `m11-quality-gate`. La opcion recomendada es no cambiar
  defaults productivos hasta que una corrida compare mejoras, regresiones y
  costo por limite.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
