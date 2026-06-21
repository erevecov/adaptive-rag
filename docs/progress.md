# Progreso de Adaptive RAG

## Milestone activo

Pendiente de abrir el siguiente change OpenSpec.

## Ultimo milestone completado

M13 Chat audit trail cerrado el 2026-06-21.

## Ultimo slice completado

M13 `m13-closeout`: archiva `m13-chat-audit-trail`, publica la spec canonica
`chat-audit-trail` y reconcilia el estado de progreso/roadmap despues del merge
de PR #69.

Comandos validados:

```text
uv run pytest
npx --yes @fission-ai/openspec archive m13-chat-audit-trail --yes
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

Ninguno.

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

- Abrir un nuevo change OpenSpec solo despues de elegir prioridad para M14.
  La opcion recomendada es una superficie de lectura/historial de chat sobre el
  audit trail durable, antes de streaming SSE o dashboards. La razon es que M13
  ya deja sesiones, mensajes, tool calls, retrieval runs, citations y usage/cost
  persistidos, pero todavia no hay contrato publico para consultarlos de forma
  aislada por proyecto.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
