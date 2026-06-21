# Progreso de Adaptive RAG

## Milestone activo

M15 Chat frontend inicial.

## Ultimo milestone completado

M14 Chat history/read surface cerrado el 2026-06-21.

## Ultimo slice completado

M15 `m15-chat-frontend-plan`: abre el change OpenSpec para una primera UI de
chat e historial sobre los contratos existentes `POST /chat` y `chat-history`.
El PR de planificacion no agrega dependencias Node ni codigo frontend
productivo.

Comandos validados en este PR:

```text
npx --yes @fission-ai/openspec validate m15-chat-frontend-plan --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
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

- Implementar `m15-frontend-scaffold`: crear `frontend/` con
  React/TypeScript/Vite, scripts de dev/build/lint/test y documentacion local.
  La razon es que el repo no tiene frontend ni lockfile Node, y conviene fijar
  el scaffold antes de integrar el cliente API y la UI.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
