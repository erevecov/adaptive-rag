# Arquitectura

Esta carpeta contiene lineas base de arquitectura y producto que orientan varios
changes OpenSpec.

Documentos:

- `v1-design.md`: linea base de arquitectura y alcance v1.
- `retrieval-decision-gates.md`: criterios para abrir o rechazar futuros
  experimentos de lexical/RRF, sparse retrieval o tuning de retrieval.
- `retrieval-strategy-decision.md`: decision M11 para ejecutar primero tuning
  de `candidate_limit` y mantener lexical/RRF y Qwen sparse en hold.
- `candidate-limit-ab-evidence.md`: evidencia M11 del runner A/B offline y
  decision de mantener la superficie API/CLI de candidate tuning en hold.
- `retrieval-evidence-expansion.md`: decision M12 para ampliar evidencia sobre
  distractors y lexical misses antes de abrir nuevas estrategias de retrieval.
- `retrieval-strategy-refresh-m12.md`: evidencia M12 actualizada y decision de
  mantener dense default sin promover candidate tuning, lexical/RRF ni sparse.
- `qwen-local-models.md`: snapshot 2026-06-22 sobre modelos Qwen levantables en
  local para chat, routing, embeddings, rerank, sparse y voz.
- `v1-release-readiness-m21.md`: decision M21 para recortar v1.0 al core
  demostrable post-M20, clasificar deferrals y preparar release package/demo.
- `v1-release-package.md`: runbook M21 para ejecutar API, worker
  project-scoped, Postgres/pgvector y demo offline reproducible sin servicios
  hosted obligatorios.
- `chat-audit-trail-m13.md`: decision M13 para persistir sesiones, mensajes,
  tool calls, retrieval runs, citations y usage/cost antes de streaming,
  dashboards o historial.
- `chat-history-m14.md`: decision M14 para exponer listado/detalle read-only de
  sesiones antes de frontend, streaming o dashboards.
- `chat-frontend-m15.md`: decision M15 para construir una UI inicial de chat e
  historial sobre `POST /chat` y `chat-history`.
- `chat-streaming-m16.md`: decision M16 para exponer chat streaming por SSE
  sobre `POST`, con frontend `fetch` streaming, cancelacion, fallback y audit
  trail compatible.
- `chat-observability-m17.md`: decision M17 para exponer observability
  local-first de chat, costo y latencia via API/CLI read-only sobre audit trail
  existente.
- `chat-observability-dashboard-m20.md`: decision M20 para exponer un dashboard
  frontend read-only y ligero sobre el resumen M17 y el historial M14.
- `neo4j-graph-db-m18.md`: decision M18 para evaluar Neo4j como graph DB
  routeable, manteniendo Postgres como fuente durable y graph DB como indice
  derivado opt-in.
- `graph-db-decision-matrix-m18.md`: matriz M18 que selecciona Neo4j como
  primer backend live opt-in y mantiene Memgraph/FalkorDB/Kuzu en hold/no-go.
- `graph-store-contract-m18.md`: contrato M18 de `GraphStore`, settings,
  readiness/backfill en Postgres, errores estables y fakes offline antes de
  Neo4j live.
- `neo4j-adapter-health-m18.md`: adapter Neo4j opt-in, dependencia driver,
  health check con `verify_connectivity()` y mapeo de errores estables.
- `neo4j-indexer-m18.md`: indexer Neo4j idempotente por `project_id`, con
  payload derivado desde Postgres y relaciones iniciales de project/source/
  document/version/chunk.
- `graph-retrieval-route-m18.md`: ruta retrieval graph opt-in sobre seeds dense,
  fallback dense con `fallback_reason` estable y citations rehidratadas desde
  Postgres.
- `graph-quality-gate-m18.md`: gate M18 dense-vs-graph con reporte versionado,
  decision `hold_default` y cierre conservador sin cambiar defaults.
- `graph-live-ops-m19.md`: plan M19 para medir Neo4j live, backfill/reindex,
  latencia, fallback y costo operacional antes de cualquier promocion de
  defaults.
- `neo4j-live-harness-m19.md`: smoke CLI opt-in para validar conectividad
  Neo4j local/managed sin exponer secretos ni cambiar defaults.
- `graph-backfill-reindex-m19.md`: comandos CLI opt-in para reconstruir la
  proyeccion Neo4j por proyecto y persistir readiness/error codes.
- `graph-retrieval-smoke-m19.md`: smoke CLI opt-in para validar retrieval
  `strategy=graph` con proyeccion ready, citations y fallback visible.
- `graph-live-evidence-report-m19.md`: reporte M19 que consolida el quality
  gate dense-vs-graph con artefactos live de backfill/reindex, retrieval smoke,
  error codes, latencia/fallback y costo operacional declarado.

Reglas:

- OpenSpec manda para contratos implementados o en implementacion.
- Estos documentos pueden explicar contexto, tradeoffs y direccion de producto.
- No se usan para tracking de tareas ni para registrar progreso diario.
- Si una decision arquitectonica se convierte en trabajo ejecutable, debe pasar
  por `openspec/changes/<change-id>/`.
