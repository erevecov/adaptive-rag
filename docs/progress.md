# Progreso de Adaptive RAG

## Milestone activo

M16 Chat streaming SSE.

## Ultimo milestone completado

M15 Chat frontend inicial cerrado el 2026-06-21.

## Ultimo slice completado

M16 `m16-chat-streaming-sse`: abre el change OpenSpec para definir streaming de
chat por SSE sobre la UI y el audit trail existentes, usando `POST` con
`text/event-stream`, consumo frontend via `fetch` streaming, evento `final`
compatible con `POST /chat` y fallback no streaming.

Comandos validados en este slice:

```text
pnpm dlx ctx7@latest library "FastAPI" "How to implement streaming HTTP responses for Server-Sent Events using FastAPI StreamingResponse with async generators and text/event-stream"
pnpm dlx ctx7@latest docs /fastapi/fastapi "How to implement streaming HTTP responses for Server-Sent Events using FastAPI StreamingResponse with async generators and text/event-stream"
uv run python -c "import fastapi; print(fastapi.__version__); import importlib.util; print(importlib.util.find_spec('fastapi.sse') is not None)"
pnpm dlx @fission-ai/openspec validate m16-chat-streaming-sse --strict
pnpm dlx @fission-ai/openspec validate --specs --strict
pnpm dlx @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- `m16-chat-streaming-sse`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-21-m15-chat-frontend-plan/`

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

## Siguiente tarea recomendada

- Implementar `m16-streaming-event-contract`: definir modelos/eventos y
  serializer SSE determinista antes del endpoint FastAPI y la UI. La razon es
  que backend y frontend deben compartir un contrato de eventos estable antes de
  conectar streaming real.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
