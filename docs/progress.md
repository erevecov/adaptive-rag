# Progreso de Adaptive RAG

## Milestone activo

M6 Evals.

## Ultimo milestone completado

M5 Chat/tool calling cerrado el 2026-06-19.

## Ultimo slice completado

M6 `m6-retrieval-eval-runner`: agrega un runner offline que construye un
proyecto fixture-backed desde suites locales, ejecuta `RetrievalService` con
provider fake/determinista y reporta metricas top-k/expected evidence con
citations observadas, sin chat ni CLI todavia.

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

- `m6-chat-eval-runner`: ejecutar los casos de chat contra `ChatService` con
  runner fake y retrieval fixture-backed. Es la opcion recomendada porque
  retrieval ya tiene un harness offline reutilizable; ahora falta verificar
  citations, tool calls y ausencia de evidence inventada antes de publicar CLI.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
