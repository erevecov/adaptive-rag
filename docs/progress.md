# Progreso de Adaptive RAG

## Milestone activo

M8 Hosted evals.

## Ultimo milestone completado

M7 Provider runtime cerrado el 2026-06-19.

## Ultimo slice completado

M8 `m8-live-provider-evals-plan`: crea el change OpenSpec para hosted evals
opt-in sobre `evals-baseline` y `provider-runtime`, definiendo una secuencia
para medir calidad/costo de Qwen live sin cambiar el gate offline por defecto.

Comandos validados:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m8-live-provider-evals-plan --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

Este slice es de planificacion y no requiere credenciales live.

## Change OpenSpec activo

- `openspec/changes/m8-live-provider-evals-plan/`

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

## Siguiente tarea recomendada

- Implementar `m8-hosted-eval-contract`. Es el siguiente slice recomendado
  porque define modo hosted, modelos de reporte usage/cost, presupuesto maximo
  de corrida y errores estables antes de conectar runners live o cambiar la CLI.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
