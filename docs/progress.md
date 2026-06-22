# Progreso de Adaptive RAG

## Milestone activo

M21 V1 release readiness.

M21 convierte el estado post-M20 en una checklist de release v1.0. El objetivo
es decidir que entra en v1.0, que se difiere a post-v1 y que trabajo final
falta para un release local-first demostrable.

## Ultimo milestone completado

M20 Chat observability dashboard cerrado el 2026-06-22.

M20 convierte el resumen read-only de observability de M17 en una vista
frontend operativa. El layout aprobado es hibrido: filtros superiores, metric
cards, breakdowns, provider usage table y session health table.

M20 no cambia retrieval, rerank, providers, streaming ni graph defaults. La
decision M19 sigue vigente: Neo4j queda en `hold_default` hasta contar con
evidencia live concluyente.

## Ultimo slice completado

M20 `m20-quality-gate`: valida frontend, Python, OpenSpec y smokes CLI;
archiva el change M20 y publica los requisitos canonicos en
`chat-frontend` y `chat-observability`.

Este cierre no agrega endpoints backend, no consulta tablas internas y no
modifica defaults de retrieval, rerank, providers, streaming ni graph.

Comandos validados en el gate M20:

```text
pnpm --dir frontend test
pnpm --dir frontend run typecheck
pnpm --dir frontend run lint
uv run pytest
pnpm --dir frontend run build
uv run ruff check .
uv run mypy src
uv run adaptive-rag version
uv run adaptive-rag health
npx --yes @fission-ai/openspec validate m20-chat-observability-dashboard-plan --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- `openspec/changes/m21-v1-release-readiness-plan/`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-22-m20-chat-observability-dashboard-plan/`

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
- `openspec/specs/chat-observability/spec.md`
- `openspec/specs/graph-store/spec.md`

## Siguiente tarea recomendada

- Completar y mergear `m21-v1-release-readiness-plan`. Despues, la opcion
  recomendada es `m21-v1-scope-reconciliation` para actualizar
  `docs/architecture/v1-design.md` con items `in_v1`, `defer_post_v1` y
  `blocked` antes de tocar packaging, README o demo.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
