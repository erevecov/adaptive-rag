# M18 Neo4j indexer

Fecha: 2026-06-22.

## Decision

`m18-neo4j-indexer` materializa en Neo4j un indice derivado y reconstruible
desde Postgres por `project_id`. Postgres sigue siendo la fuente durable; Neo4j
solo recibe facts serializados para project, sources, documents, document
versions, chunks y links de chunks.

El indexer no cambia el default `graph_store=disabled` ni activa retrieval
graph. Solo deja listo el backfill idempotente para un proyecto cuando el
backend Neo4j esta opt-in.

## Implementacion

- `load_project_graph(session, project_id)` construye un `Neo4jProjectGraph`
  determinista desde tablas canonicas de Postgres.
- El payload conserva aislamiento por `project_id`, metadata serializada como
  JSON estable y anclas de citations por `document_version_id`, `char_start` y
  `char_end`.
- No copia embeddings densos ni `normalized_text` completo a Neo4j; esos datos
  siguen en Postgres/pgvector.
- `Neo4jGraphStore.backfill_project_graph(...)` requiere un
  `project_graph_loader`, elimina nodos `AdaptiveRagGraph` del proyecto y luego
  ejecuta `MERGE` de nodos/relaciones.
- `get_graph_store(...)` inyecta el loader Postgres por default para stores
  runtime creados con `graph_store=neo4j`; tests pueden inyectar loaders sin red.
- `delete_project_graph(...)` borra solo nodos etiquetados
  `AdaptiveRagGraph` con el `project_id` solicitado.
- Errores `ServiceUnavailable`/`DriverError` se mapean a
  `graph_store_unavailable`; errores Neo4j de query se mapean a
  `graph_store_query_failed`.

## Grafo materializado

- `AdaptiveRagProject`
- `AdaptiveRagSource`
- `AdaptiveRagDocument`
- `AdaptiveRagDocumentVersion`
- `AdaptiveRagChunk`

Relaciones iniciales:

- `(:AdaptiveRagProject)-[:HAS_SOURCE]->(:AdaptiveRagSource)`
- `(:AdaptiveRagSource)-[:HAS_DOCUMENT]->(:AdaptiveRagDocument)`
- `(:AdaptiveRagDocument)-[:HAS_VERSION]->(:AdaptiveRagDocumentVersion)`
- `(:AdaptiveRagDocumentVersion)-[:HAS_CHUNK]->(:AdaptiveRagChunk)`
- `(:AdaptiveRagChunk)-[:NEXT_CHUNK]->(:AdaptiveRagChunk)`

## Fuera de alcance

- Worker/job/CLI de reindex.
- Route de retrieval graph.
- Audit trail de estrategia graph.
- Evals comparativas dense vs graph-enabled.
- Cambios de defaults de retrieval.

## Siguiente paso

`m18-graph-retrieval-route` debe consumir este indice solo en modo opt-in,
mantener fallback dense cuando el graph store este disabled/unavailable o la
proyeccion no este `ready`, y preservar citations/audit trail.
