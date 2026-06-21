# Progreso de Adaptive RAG

## Milestone activo

M17 Chat observability y costo-latencia.

## Ultimo milestone completado

M16 Chat streaming SSE cerrado el 2026-06-21.

## Ultimo slice completado

M17 `m17-observability-read-models`: agrega read models y
`ChatObservabilityRepository` para resumir sesiones, provider usage,
costo/usage, latencias y errores por proyecto usando el audit trail existente.
El resumen aplica filtros de fecha/status, mantiene aislamiento por proyecto y
calcula percentiles de latencia en Python para que los tests locales sean
portables.

Comandos validados en este slice:

```text
uv run pytest
uv run ruff check src tests
uv run mypy src/adaptive_rag
pnpm dlx @fission-ai/openspec validate m17-chat-observability --strict
pnpm dlx @fission-ai/openspec validate --specs --strict
git diff --check
```

## Change OpenSpec activo

- `m17-chat-observability`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-21-m16-chat-streaming-sse/`

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
- `openspec/specs/chat-history/spec.md`
- `openspec/specs/chat-frontend/spec.md`
- `openspec/specs/chat-streaming/spec.md`

## Siguiente tarea recomendada

- Implementar `m17-observability-api`: exponer
  `GET /projects/{project_id}/chat/observability/summary` reutilizando
  `ChatObservabilityRepository`. La razon es fijar primero el contrato HTTP y
  la validacion de filtros antes de agregar el comando CLI equivalente.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
