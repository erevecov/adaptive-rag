# M19 graph backfill/reindex ops

`m19-graph-backfill-reindex-ops` hace operable el indice Neo4j derivado antes
de correr retrieval graph live. La fuente durable sigue siendo Postgres y Neo4j
se reconstruye por `project_id`.

## Superficie CLI

```bash
uv run adaptive-rag graph backfill <project-id> --source-watermark chunks:v1
uv run adaptive-rag graph reindex <project-id> --source-watermark chunks:v2
```

Ambos comandos usan `graph_store=neo4j` cuando esta configurado por settings.
La salida es JSON y contiene:

- `project_id`
- `backend`
- `operation`
- `previous_status`
- `status`
- `source_watermark`
- `duration_ms`
- `node_count`
- `relationship_count`
- `error_code`

El comando sale con codigo `0` solo cuando el reporte termina en `ready`.
Si Neo4j, el loader o la configuracion fallan, la proyeccion queda en `failed`
con un error code estable y el comando sale con codigo `1`.

## Transiciones

La operacion comparte un orquestador reutilizable:
`run_graph_backfill_operation(...)`.

Flujo esperado:

1. Lee el estado previo de `graph_projections`.
2. Marca `pending_backfill` con el `source_watermark` solicitado.
3. Marca `indexing`.
4. Ejecuta `GraphStore.backfill_project_graph(...)`.
5. Marca `ready` con `last_indexed_at` si Neo4j completa.
6. Marca `failed` con `graph_store_misconfigured`,
   `graph_store_unavailable` o `graph_store_query_failed` si falla.

El adapter Neo4j sigue borrando solo nodos `AdaptiveRagGraph` del proyecto y
luego materializa project, sources, documents, document versions, chunks y
links derivados desde Postgres.

## Fuera de alcance

- No promueve `strategy=graph` como default.
- No cambia `graph_store=disabled` como default.
- No ejecuta retrieval graph live; eso queda para
  `m19-graph-live-retrieval-smoke`.
