# Progreso de Adaptive RAG

## Milestone activo

M15 Chat frontend inicial.

## Ultimo milestone completado

M14 Chat history/read surface cerrado el 2026-06-21.

## Ultimo slice completado

M15 `m15-chat-api-client`: agrega Vitest y un cliente `fetch` tipado para
`POST /projects/{project_id}/chat`,
`GET /projects/{project_id}/chat/sessions` y
`GET /projects/{project_id}/chat/sessions/{session_id}`. El cliente serializa
JSON estable, construye query params opcionales y expone errores HTTP
estructurados sin integrar todavia componentes visuales.

Comandos validados en este slice:

```text
pnpm dlx ctx7@latest library Vitest "Add Vitest tests for a TypeScript fetch API client in a Vite React app using pnpm"
pnpm dlx ctx7@latest docs /vitest-dev/vitest "Add Vitest tests for a TypeScript fetch API client in a Vite React app using pnpm"
cd frontend && pnpm add -D vitest
cd frontend && pnpm test
cd frontend && pnpm run lint
cd frontend && pnpm run typecheck
cd frontend && pnpm run build
pnpm dlx @fission-ai/openspec validate m15-chat-frontend-plan --strict
pnpm dlx @fission-ai/openspec validate --specs --strict
pnpm dlx @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- `m15-chat-frontend-plan`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-21-m14-chat-history-read-surface/`

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

## Siguiente tarea recomendada

- Implementar `m15-chat-workspace-ui`: conectar el shell existente con el
  cliente API para enviar preguntas, mostrar answer/citations/tool calls y
  refrescar historial despues de una respuesta exitosa. La razon es que el
  contrato TypeScript ya esta cubierto por tests antes de construir la UI.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
