# Progreso de Adaptive RAG

## Milestone activo

No hay milestone activo.

M20 Chat observability dashboard quedo completado y archivado el 2026-06-22.

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

- Ninguno.

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

- Despues de mergear el cierre M20, sincronizar `main` y abrir un nuevo
  change OpenSpec para el siguiente milestone antes de implementar. No hace
  falta abrir `m20-observability-summary-shape` porque el summary M17 cubrio
  los breakdowns sin campos nuevos.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
