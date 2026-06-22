# Progreso de Adaptive RAG

## Milestone activo

M20 Chat observability dashboard.

M20 convierte el resumen read-only de observability de M17 en una vista
frontend operativa. El layout aprobado es hibrido: filtros superiores, metric
cards, breakdowns, provider usage table y session health table.

## Ultimo milestone completado

M19 Graph live ops evidence cerrado el 2026-06-22.

Decision: `hold_default`. Neo4j sigue como indice derivado opt-in,
`graph_store=disabled` y `strategy=dense` siguen como defaults, y cualquier
rollout/default requiere un milestone posterior con evidencia live concluyente.

## Ultimo slice completado

M19 `m19-quality-gate`: valida el milestone completo, archiva
`m19-graph-live-ops-plan`, publica los requisitos M19 en
`openspec/specs/graph-store/spec.md` y preserva la decision conservadora
`hold_default`.

Los smokes live Neo4j no se ejecutaron en el gate local porque el worktree no
tenia `.env` ni variables `ADAPTIVE_RAG_GRAPH_STORE`/`ADAPTIVE_RAG_NEO4J_*`
configuradas.

Comandos validados en este slice:

```text
uv run pytest
uv run ruff check src tests
uv run mypy src/adaptive_rag
npx --yes @fission-ai/openspec validate m19-graph-live-ops-plan --strict
npx --yes @fission-ai/openspec archive m19-graph-live-ops-plan --yes
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- `openspec/changes/m20-chat-observability-dashboard-plan/`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-22-m19-graph-live-ops-plan/`

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

- Completar y mergear `m20-chat-observability-dashboard-plan`. Despues, la
  opcion recomendada es `m20-observability-frontend-client` para agregar tipos
  y cliente frontend de
  `GET /projects/{project_id}/chat/observability/summary` antes de construir
  la UI.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
