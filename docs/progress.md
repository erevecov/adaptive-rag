# Progreso de Adaptive RAG

## Milestone activo

Ninguno. El siguiente milestone recomendado es M6 Evals.

## Ultimo milestone completado

M5 Chat/tool calling cerrado el 2026-06-19.

## Ultimo slice completado

M5 `m5-quality-gate`: valida el milestone completo, archiva
`m5-chat-tool-calling-plan` y publica
`openspec/specs/chat-tool-calling/spec.md` como spec canonica.

Comandos validados:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate m5-chat-tool-calling-plan --strict
openspec list
openspec validate --specs --strict
uv run adaptive-rag version
uv run adaptive-rag health
uv run adaptive-rag retrieval search --help
uv run adaptive-rag chat ask --help
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

## Siguiente tarea recomendada

- `m6-evals-plan`: abrir un change OpenSpec para definir evaluaciones offline
  de retrieval/chat antes de streaming, persistencia de conversaciones o
  providers live. Es la opcion recomendada porque el sistema ya puede responder
  con citations, pero todavia no tiene una forma canonica de medir calidad,
  groundedness y regresiones.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
