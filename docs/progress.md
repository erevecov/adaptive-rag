# Progreso de Adaptive RAG

## Milestone activo

M14 Chat history/read surface.

## Ultimo milestone completado

M13 Chat audit trail cerrado el 2026-06-21.

## Ultimo slice completado

M14 `m14-chat-history-api`: agrega schemas HTTP y endpoints read-only para
listar sesiones de chat y consultar el detalle auditable de una sesion. El
listado conserva aislamiento por proyecto, filtro de status, limite acotado,
cursor deterministico, conteos y costo estimado; el detalle devuelve metadata
de sesion, mensajes, tool calls, retrieval runs con retrieved chunks/citations
anidadas y provider usage, sin re-ejecutar chat/retrieval ni mutar el audit
trail.

Comandos validados:

```text
uv run pytest tests/integration/api/test_chat.py -q
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m14-chat-history-read-surface --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- `openspec/changes/m14-chat-history-read-surface/`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-21-m13-chat-audit-trail/`

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
- `openspec/specs/chat-audit-trail/spec.md`

## Siguiente tarea recomendada

- Implementar `m14-chat-history-cli`: comandos
  `adaptive-rag chat sessions list` y `adaptive-rag chat sessions show` con
  salida JSON estable sobre los mismos read models. La razon es cerrar la
  inspeccion local/QA de historial antes del quality gate y antes de iniciar
  frontend, streaming o dashboards.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
