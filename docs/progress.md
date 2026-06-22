# Progreso de Adaptive RAG

## Milestone activo

M19 Graph live ops evidence.

Objetivo: medir y operar Neo4j live como indice derivado opt-in antes de
considerar cualquier promocion de graph retrieval. `dense` sigue como default y
`graph` sigue limitado a experimentos controlados.

## Ultimo milestone completado

M18 Neo4j graph DB decision cerrado el 2026-06-22.

## Ultimo slice completado

M18 `m18-evals-quality-gate`: agrega un gate dense-vs-graph para comparar
`strategy=dense` contra `strategy=graph` en suites versionadas, con metricas de
hit rate, best-rank delta, regresiones, metadata filters, citation coverage y
costo provider incremental. La decision queda `hold_default`: graph retrieval
sigue opt-in y dense sigue como default.

Comandos validados en este slice:

```text
pnpm dlx @fission-ai/openspec validate m18-neo4j-graph-db-decision --strict
pnpm dlx @fission-ai/openspec archive m18-neo4j-graph-db-decision --yes
pnpm dlx @fission-ai/openspec validate --specs --strict
pnpm dlx @fission-ai/openspec list
uv run pytest
uv run ruff check src tests
uv run mypy src/adaptive_rag
git diff --check
```

## Change OpenSpec activo

- `openspec/changes/m19-graph-live-ops-plan/`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-22-m18-neo4j-graph-db-decision/`

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

- Implementar `m19-neo4j-local-managed-harness`: documentar setup local/managed
  de Neo4j live y agregar un smoke opt-in de connectivity/settings antes de
  construir backfill/reindex operativo. Es la opcion recomendada porque valida
  el entorno real y errores estables antes de depender de Neo4j en operaciones
  mas largas.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
