# Progreso de Adaptive RAG

## Milestone activo

Pendiente de abrir el siguiente change OpenSpec.

## Ultimo milestone completado

M11 Retrieval strategy decision cerrado el 2026-06-20.

## Ultimo slice completado

M11 `m11-quality-gate`: valida el milestone completo, ejecuta smokes live Qwen
opt-in con `.env` local, archiva `m11-retrieval-strategy-decision` y publica la
spec canonica actualizada de `retrieval-quality`.

Comandos validados:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m11-retrieval-strategy-decision --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec archive m11-retrieval-strategy-decision --yes
npx --yes @fission-ai/openspec list
git diff --check
```

Smokes hosted Qwen opt-in validados con `.env` local:

```text
adaptive-rag providers embedding-smoke
adaptive-rag providers chat-smoke
adaptive-rag providers rerank-smoke
hosted retrieval eval reranked con `retrieval-dataset-pack`, SQLite temporal,
`candidate_limit=8` y `max_cost_usd=0.20`
```

## Change OpenSpec activo

Ninguno.

## Ultimo change archivado

- `openspec/changes/archive/2026-06-20-m11-retrieval-strategy-decision/`

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

- Abrir el siguiente change OpenSpec solo despues de elegir una prioridad nueva.
  La opcion recomendada es atacar evidencia adicional de retrieval en vez de
  agregar algoritmos: ampliar casos de distractors/lexical misses y decidir si
  lexical/RRF merece `proceed`, manteniendo dense retrieval como default.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
