# Progreso de Adaptive RAG

## Milestone activo

M6 Evals.

## Ultimo milestone completado

M5 Chat/tool calling cerrado el 2026-06-19.

## Ultimo slice completado

M6 `m6-evals-fixtures-contract`: agrega el paquete `adaptive_rag.evals` con
modelos internos, errores estables, loader estricto de suites JSON locales y
serializacion determinista de reportes, sin runners ni CLI todavia.

Comandos validados:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate m6-evals-plan --strict
openspec list
openspec validate --specs --strict
git diff --check
```

## Change OpenSpec activo

- `m6-evals-plan`

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

## Siguiente tarea recomendada

- `m6-retrieval-eval-runner`: ejecutar los casos de retrieval contra
  `RetrievalService` usando suites locales y provider fake. Es la opcion
  recomendada porque el contrato de fixtures ya puede declarar casos, expected
  evidence y thresholds; ahora falta medir top-k/expected chunk antes de sumar
  chat o CLI.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
