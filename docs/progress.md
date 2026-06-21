# Progreso de Adaptive RAG

## Milestone activo

M16 Chat streaming SSE.

## Ultimo milestone completado

M15 Chat frontend inicial cerrado el 2026-06-21.

## Ultimo slice completado

M16 `m16-streaming-event-contract`: agrega el contrato interno de eventos SSE
para chat, con factories para `session_started`, `tool_call`, `answer_delta`,
`heartbeat`, `final` y `error`, serializer determinista de framing SSE y tests
unitarios que verifican que `final` reutiliza el shape de `POST /chat`.

Comandos validados en este slice:

```text
uv run pytest tests/unit/chat/test_chat_streaming.py
uv run pytest
uv run ruff check .
uv run mypy src
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

- Implementar `m16-chat-service-streaming`: compartir validacion, audit trail,
  retrieval tool, citations y provider usage con el flujo no streaming antes de
  exponer el endpoint FastAPI. La razon es mantener un unico contrato de negocio
  antes de conectar transporte SSE.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
