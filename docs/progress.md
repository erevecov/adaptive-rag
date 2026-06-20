# Progreso de Adaptive RAG

## Milestone activo

M9 Retrieval quality/rerank.

## Ultimo milestone completado

M8 Hosted evals cerrado el 2026-06-20.

## Ultimo slice completado

M9 `m9-rerank-api-cli-surface`: expone rerank opt-in en
`POST /projects/{project_id}/retrieval/search` mediante
`rerank.candidate_limit` y en `adaptive-rag retrieval search` mediante
`--rerank-candidate-limit`, validando limites antes de construir el provider y
manteniendo el payload dense existente cuando rerank no se usa.

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

- Implementar `m9-rerank-hosted-evals`. Es la opcion recomendada porque el
  rerank ya esta disponible en provider, servicio y superficies; el siguiente
  riesgo es medir calidad/costo frente al baseline dense en evals hosted.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
