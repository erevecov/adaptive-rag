# Progreso de Adaptive RAG

## Milestone activo

M9 Retrieval quality/rerank.

## Ultimo milestone completado

M8 Hosted evals cerrado el 2026-06-20.

## Ultimo slice completado

M9 `m9-rerank-provider-contract`: agrega contratos provider-neutral de rerank,
fake deterministic default, settings/factory runtime para seleccionar fake o
Qwen sin llamadas live, errores estables de configuracion/request y wiring de
budget/price catalog para el siguiente adapter live.

Comandos validados:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m9-retrieval-quality-rerank-plan --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

No se ejecutaron smokes hosted: este slice no agrega el adapter HTTP live de
Qwen rerank ni requiere credenciales.

## Change OpenSpec activo

- `openspec/changes/m9-retrieval-quality-rerank-plan/`

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

## Siguiente tarea recomendada

- Implementar `m9-live-qwen-rerank-provider`. Es la opcion recomendada porque
  el contrato/factory ya esta fijado con fake default; el siguiente riesgo es
  conectar Qwen rerank con cliente HTTP, usage/cost, budget guard, timeouts y
  smoke live opt-in antes de integrarlo en `RetrievalService`.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
