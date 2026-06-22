# Progreso de Adaptive RAG

## Milestone activo

Ninguno. Siguiente paso: decidir M19.

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

- Ninguno.

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

- Decidir M19. La opcion recomendada es un milestone de evidencia/operacion
  graph live si se quiere avanzar Neo4j: medir latencia/costo operacional con
  Neo4j real y definir reindex/backfill operable antes de considerar cualquier
  promocion de default.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
