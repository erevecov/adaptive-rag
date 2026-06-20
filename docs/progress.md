# Progreso de Adaptive RAG

## Milestone activo

M11 Retrieval strategy decision.

## Ultimo milestone completado

M10 Retrieval eval datasets y decision gates cerrado el 2026-06-20.

## Ultimo slice completado

M10 `m10-quality-gate`: valida el milestone completo, ejecuta smokes offline y
hosted Qwen opt-in, archiva `m10-retrieval-eval-datasets-plan` y sincroniza la
spec canonica `retrieval-quality`.

Comandos validados:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
uv run adaptive-rag evals run evals/fixtures/retrieval-smoke.json --mode offline
uv run adaptive-rag evals run evals/fixtures/chat-smoke.json --mode offline
uv run adaptive-rag providers rerank-smoke
uv run adaptive-rag evals run evals/fixtures/retrieval-rerank-smoke.json --mode hosted --max-cost-usd 0.05 --rerank-candidate-limit 2
npx --yes @fission-ai/openspec archive m10-retrieval-eval-datasets-plan --yes
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

- Despues de mergear `m11-retrieval-strategy-decision`, implementar
  `m11-candidate-limit-eval-matrix`. Es la opcion recomendada porque candidate
  tuning reutiliza dense/rerank y el harness M10 sin agregar indexes, storage ni
  providers nuevos; lexical/RRF y Qwen sparse quedan en hold hasta tener
  evidencia/docs especificas.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
