# Progreso de Adaptive RAG

## Milestone activo

M7 Provider runtime.

## Ultimo milestone completado

M6 Evals cerrado el 2026-06-19.

## Ultimo slice completado

M7 `m7-usage-cost-limits`: agrega `provider_usage` con records estructurados,
tracker in-memory, price catalog configurable, budget guard por request/corrida
y wiring en clientes Qwen HTTP de embeddings/chat. Los smokes CLI ahora
devuelven errores estables si el budget bloquea una llamada.

Comandos validados:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
uv run adaptive-rag providers chat-smoke --message "What supports alpha?"
openspec validate m7-provider-runtime-plan --strict
openspec validate --specs --strict
openspec list
git diff --check
```

## Change OpenSpec activo

- `openspec/changes/m7-provider-runtime-plan/`

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

## Siguiente tarea recomendada

- Ejecutar `m7-quality-gate` y archivar el change. Es el siguiente slice
  recomendado porque settings, embeddings live, chat live y usage/cost limits
  ya quedan implementados; falta reconciliar specs/docs y publicar
  `provider-runtime` como spec canonica.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
