# Progreso de Adaptive RAG

## Milestone activo

M18 Neo4j graph DB decision.

## Ultimo milestone completado

M17 Chat observability y costo-latencia cerrado el 2026-06-21.

## Ultimo slice completado

M18 `m18-neo4j-graph-db-decision`: crea el change OpenSpec M18, define la
capacidad `graph-store`, documenta la decision Neo4j routeable y actualiza
arquitectura/roadmap/progreso. Este slice no cambia codigo productivo,
settings, dependencias, migrations, frontend ni infraestructura.

Comandos validados en este slice:

```text
pnpm dlx @fission-ai/openspec validate m18-neo4j-graph-db-decision --strict
pnpm dlx @fission-ai/openspec validate --specs --strict
pnpm dlx @fission-ai/openspec list
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

- Continuar con `m18-graph-db-decision-matrix`, porque antes de agregar
  dependencias o adapter live conviene comparar Neo4j contra FalkorDB,
  Memgraph, Kuzu y no-op con evidencia verificable de setup local, managed,
  drivers, costos, operaciones y testability.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
