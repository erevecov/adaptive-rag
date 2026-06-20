# Progreso de Adaptive RAG

## Milestone activo

Ninguno. M10 queda pendiente de planificacion OpenSpec.

## Ultimo milestone completado

M9 Retrieval quality/rerank cerrado el 2026-06-20.

## Ultimo slice completado

M9 `m9-quality-gate`: valida el milestone completo, ejecuta smokes Qwen live
opt-in para rerank y hosted eval reranked, archiva el change
`m9-retrieval-quality-rerank-plan` y publica
`openspec/specs/retrieval-quality/spec.md` como spec canonica.

Comandos validados:

```text
uv sync --extra dev
uv run pytest
uv run adaptive-rag providers rerank-smoke --query "What supports alpha?" --document "Beta only" --document "Alpha evidence supports smoke retrieval." --top-k 1
uv run adaptive-rag evals run evals/fixtures/retrieval-rerank-smoke.json --mode hosted --provider qwen --max-cost-usd 0.05 --rerank-candidate-limit 2
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec archive m9-retrieval-quality-rerank-plan --yes
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
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
- `openspec/specs/chat-tool-calling/spec.md`
- `openspec/specs/evals-baseline/spec.md`
- `openspec/specs/provider-runtime/spec.md`
- `openspec/specs/hosted-evals/spec.md`
- `openspec/specs/retrieval-quality/spec.md`

## Siguiente tarea recomendada

- Abrir un change OpenSpec para M10. Es la opcion recomendada porque M9 ya
  cerro rerank opt-in y medicion hosted; antes de implementar lexical/RRF o
  tuning adicional, conviene definir el objetivo de calidad, datasets de eval
  mas amplios y criterios de decision.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
