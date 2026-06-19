# Progreso de Adaptive RAG

## Milestone activo

M5 Chat/tool calling.

## Ultimo milestone completado

M4 Superficie de retrieval cerrado el 2026-06-19.

## Ultimo slice completado

M5 `m5-chat-cli-command`: agrega `adaptive-rag chat ask` como adaptador
delgado sobre `ChatService`, reutilizando `RetrievalService`,
`serialize_chat_response` y la construccion compartida de filtros CLI con
`retrieval search`.

Comandos validados:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate m5-chat-tool-calling-plan --strict
openspec list
openspec validate --specs --strict
git diff --check
```

## Change OpenSpec activo

- `m5-chat-tool-calling-plan`

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

## Siguiente tarea recomendada

- `m5-quality-gate`: validar el milestone completo y archivar
  `m5-chat-tool-calling-plan`. Es la opcion recomendada porque ya estan
  implementadas las superficies compartidas, API y CLI; queda cerrar M5 antes
  de abrir evals, streaming, persistencia de conversaciones o providers live.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
