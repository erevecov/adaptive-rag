# Progreso de Adaptive RAG

## Milestone activo

Ninguno. M16 Chat streaming SSE quedo cerrado.

## Ultimo milestone completado

M16 Chat streaming SSE cerrado el 2026-06-21.

## Ultimo slice completado

M16 `m16-quality-gate`: completa el resto del milestone en un PR. Agrega
`ChatService.stream`, `POST /projects/{project_id}/chat/stream` con
`text/event-stream`, parser SSE en el frontend, render incremental de
`answer_delta`, cancelacion con `AbortController`, fallback a `POST /chat` si
el stream falla antes de abrirse, persistencia durable del audit trail y archive
OpenSpec de `chat-streaming`.

Comandos validados en este slice:

```text
uv run pytest
uv run ruff check .
uv run mypy src
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend build
pnpm dlx @fission-ai/openspec validate m16-chat-streaming-sse --strict
pnpm dlx @fission-ai/openspec validate --specs --strict
pnpm dlx @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- Ninguno.

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

- Abrir un change OpenSpec M17 para observability de chat/costo-latencia:
  dashboard o superficie de resumen sobre el audit trail y `provider_usage`.
  La razon es que M13-M16 ya dejan sesiones, historial, usage y streaming
  persistidos; el siguiente riesgo operativo es poder ver costo, latencia,
  errores y volumen antes de agregar replay, auth final o nuevas estrategias de
  retrieval.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
