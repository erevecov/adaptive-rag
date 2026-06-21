# Progreso de Adaptive RAG

## Milestone activo

M17 Chat observability y costo-latencia.

## Ultimo milestone completado

M16 Chat streaming SSE cerrado el 2026-06-21.

## Ultimo slice completado

M17 `m17-observability-cli`: agrega
`adaptive-rag chat observability summary` reutilizando
`ChatObservabilityRepository` y el mismo schema de respuesta del endpoint HTTP.
El comando emite JSON equivalente para filtros, sesiones, provider usage,
costo/usage, latencias y errores, y reporta filtros invalidos con exit code 1.

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

- Ejecutar `m17-quality-gate`: validar Python/OpenSpec/docs, archivar
  `m17-chat-observability` y publicar la spec canonica `chat-observability`.
  La razon es cerrar M17 despues de que read model, API y CLI ya comparten el
  mismo contrato JSON.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
