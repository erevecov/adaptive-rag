# Progreso de Adaptive RAG

## Milestone activo

M14 Chat history/read surface.

## Ultimo milestone completado

M13 Chat audit trail cerrado el 2026-06-21.

## Ultimo slice completado

M14 `m14-chat-history-read-surface`: abre el change OpenSpec para exponer
lectura/historial read-only de sesiones de chat sobre el audit trail durable de
M13, sin frontend, streaming, dashboards, replay ni cambios de ranking.

Comandos validados:

```text
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

- Implementar `m14-chat-history-repository-read-models`: read models y queries
  de listado/detalle con aislamiento por proyecto, status filter, limite
  acotado y orden deterministico. La razon es que API/CLI deben apoyarse en un
  contrato de lectura compartido antes de exponer endpoints o comandos.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
