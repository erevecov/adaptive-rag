# Progreso de Adaptive RAG

## Milestone activo

M8 Hosted evals.

## Ultimo milestone completado

M7 Provider runtime cerrado el 2026-06-19.

## Ultimo slice completado

M8 `m8-hosted-eval-contract`: agrega el contrato inicial para hosted evals con
modo `offline`/`hosted`, validacion de presupuesto/credenciales, errores
estables y resumen serializable de provider usage/cost sin secretos.

Comandos validados:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
uv run pytest tests/unit/evals tests/integration/cli/test_evals_cli.py -q
npx --yes @fission-ai/openspec validate m8-live-provider-evals-plan --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

Este slice no ejecuta llamadas live; prepara el contrato para que los siguientes
runners hosted puedan compartir validacion y reporte de costo.

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

- Implementar `m8-live-retrieval-eval-runner`. Es el siguiente slice recomendado
  porque el contrato hosted ya existe y la primera medicion live debe reusar
  los fixtures de M6 materializando evidence y query embeddings con el mismo
  provider/modelo antes de sumar chat hosted.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
