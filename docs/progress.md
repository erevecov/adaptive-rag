# Progreso de Adaptive RAG

## Milestone activo

M9 Retrieval quality/rerank.

## Ultimo milestone completado

M8 Hosted evals cerrado el 2026-06-20.

## Ultimo slice completado

M9 `m9-live-qwen-rerank-provider`: conecta el contrato de rerank con el HTTP
client Qwen `qwen3-rerank`, parsea `output.results`, registra usage/cost bajo
operacion `rerank`, respeta budget guard y agrega el smoke CLI
`adaptive-rag providers rerank-smoke`.

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

Smoke hosted Qwen rerank ejecutado con `.env` local, sin imprimir secretos:

```text
rerank-smoke hosted: passed con rerank_model=qwen3-rerank
```

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

- Implementar `m9-retrieval-rerank-service`. Es la opcion recomendada porque
  el provider live ya esta disponible; el siguiente riesgo es integrarlo de
  forma opt-in despues del dense candidate set, preservando filtros, citations
  y default dense.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
