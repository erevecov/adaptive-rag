# M18 GraphStore contract

Fecha: 2026-06-21.

## Decision

`m18-graph-store-contract` fija la frontera entre Adaptive RAG y cualquier
graph DB live antes de importar el driver Neo4j. El default sigue siendo
`graph_store=disabled`; `graph_store=neo4j` queda como opt-in de configuracion,
pero todavia no construye un cliente live.

Postgres conserva la fuente canonica. Neo4j sera un indice derivado y
reconstruible por proyecto cuando los slices posteriores agreguen adapter e
indexer.

## Contrato agregado

- Settings: `graph_store=disabled|neo4j`, `neo4j_uri`, `neo4j_username` y
  `neo4j_password` opcionales.
- Contrato `GraphStore` con `health_check()`, `backfill_project_graph(...)` y
  `delete_project_graph(...)`.
- Implementaciones offline: `DisabledGraphStore` y `FakeGraphStore`.
- Errores estables: `graph_store_misconfigured`, `graph_store_unavailable` y
  `graph_store_query_failed`.
- Helper de fallback: graph retrieval solo puede evitar fallback dense cuando
  la proyeccion esta `ready`.

## Readiness en Postgres

La tabla `graph_projections` registra una fila por `project_id` y backend
`neo4j` con:

- `status`: `disabled`, `pending_backfill`, `indexing`, `ready`, `stale` o
  `failed`;
- `source_watermark`;
- `schema_version`;
- `extractor_version`;
- `last_indexed_at`;
- `error_code` y `error_message`.

El repository `GraphProjectionRepository` permite crear el estado disabled,
marcar backfill pendiente, indexing, ready, stale o failed sin hacer commit. El
caller conserva el ownership transaccional, igual que el resto de repositories
del dominio.

## Fuera de alcance

- Driver Neo4j.
- `GraphDatabase.driver(...)` o `verify_connectivity()`.
- Docker, Neo4j Desktop o Aura config.
- Indexer o reindex jobs.
- Retrieval graph online.
- Cambios de defaults de retrieval.

## Siguiente paso

`m18-neo4j-adapter-and-health` debe implementar el adapter Neo4j opt-in sobre
este contrato, validar URI/auth y mapear fallos de conectividad a errores
estables. No debe agregar indexer ni route de retrieval graph todavia.
