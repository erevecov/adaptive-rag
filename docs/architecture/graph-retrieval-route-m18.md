# M18 graph retrieval route

Fecha: 2026-06-22.

## Decision

`m18-graph-retrieval-route` agrega retrieval graph solo como opt-in. El default
sigue siendo `strategy=dense`; graph retrieval no se promueve hasta que
`m18-evals-quality-gate` compare calidad, costo, latencia, filtros y citations
contra el baseline dense.

## Implementacion

- `RetrievalSearchRequest.strategy` acepta `dense` o `graph`.
- API y CLI de retrieval exponen `strategy`, con `dense` como default.
- La ruta `graph` ejecuta dense retrieval primero para obtener chunk ids seed.
- Graph DB solo se consulta si hay `GraphRetriever` y la proyeccion del proyecto
  esta `ready` en Postgres.
- `Neo4jGraphStore.expand_project_chunks(...)` expande los chunks seed con
  `NEXT_CHUNK*0..1` dentro del `project_id`.
- Los hits graph se rehidratan desde Postgres con `DenseRetriever.get_by_chunk_ids`
  para conservar citations, filtros y metadata canonica.
- Si graph no puede usarse, el servicio vuelve a dense y agrega
  `fallback_reason` estable.
- Los payloads de retrieval exponen `strategy` y, cuando corresponde,
  `fallback_reason`.
- Chat audit conserva estrategia y fallback summary en `ToolCall`.

## Fallback reasons

- `graph_retriever_unavailable`
- `graph_projection_missing`
- `graph_projection_disabled`
- `graph_projection_pending_backfill`
- `graph_projection_indexing`
- `graph_projection_stale`
- `graph_projection_failed`
- `graph_store_unavailable`
- `graph_store_misconfigured`
- `graph_store_query_failed`

## Fuera de alcance

- Cambiar el default de retrieval.
- Agregar worker/CLI de reindex.
- Usar graph retrieval en chat como default conversacional.
- Promover graph sin evals versionadas.

## Siguiente paso

`m18-evals-quality-gate` debe comparar dense baseline vs graph-enabled retrieval
en suites versionadas y decidir si graph justifica promocion posterior.
