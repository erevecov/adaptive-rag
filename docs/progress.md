# Progreso de Adaptive RAG

## Milestone activo

M18 Neo4j graph DB decision.

## Ultimo milestone completado

M17 Chat observability y costo-latencia cerrado el 2026-06-21.

## Ultimo slice completado

M18 `m18-neo4j-adapter-and-health`: agrega `neo4j>=6.0`, `Neo4jGraphStore` y
factory `get_graph_store(...)` para crear el driver con URI/auth opt-in y
ejecutar `verify_connectivity()` solo en `health_check()`. Los fallos de auth,
servicio y driver se mapean a errores estables sin secretos. El slice no agrega
indexer, reindex jobs, retrieval graph, Docker/Aura secrets ni cambios de
default.

Comandos validados en este slice:

```text
pnpm dlx @fission-ai/openspec validate m18-neo4j-graph-db-decision --strict
pnpm dlx @fission-ai/openspec validate --specs --strict
pnpm dlx @fission-ai/openspec list
uv run pytest
uv run ruff check src tests
uv run mypy src/adaptive_rag
git diff --check
```

## Change OpenSpec activo

- `openspec/changes/m18-neo4j-graph-db-decision/`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-21-m17-chat-observability/`

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

## Siguiente tarea recomendada

- Continuar con `m18-neo4j-indexer`, porque el adapter Neo4j opt-in y health
  checks ya estan cerrados. El siguiente riesgo es materializar nodos/relaciones
  derivados desde Postgres de forma idempotente por `project_id`, sin activar
  retrieval graph ni cambiar defaults.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
