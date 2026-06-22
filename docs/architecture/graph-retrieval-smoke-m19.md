# M19 graph retrieval smoke

`m19-graph-live-retrieval-smoke` agrega una prueba operativa para confirmar que
la ruta `strategy=graph` lee desde Neo4j cuando la proyeccion del proyecto esta
`ready`.

## Superficie CLI

```bash
uv run adaptive-rag graph retrieval-smoke <project-id> --query "alpha question" --limit 5
```

El comando acepta los mismos filtros principales de retrieval:

```bash
--source-id <uuid>
--document-id <uuid>
--source-type markdown
--tag docs
--source-created-at-from 2026-06-22T00:00:00Z
--source-created-at-to 2026-06-23T00:00:00Z
--document-created-at-from 2026-06-22T00:00:00Z
--document-created-at-to 2026-06-23T00:00:00Z
```

La salida JSON resume:

- `status`: `ready`, `fallback` o `no_results`.
- `requested_strategy`: siempre `graph`.
- `result_count`, `graph_result_count` y `citation_count`.
- `fallback_reason` cuando retrieval vuelve a dense.
- `latency_ms`.
- `chunk_ids` y `source_external_ids` para inspeccion acotada.

El comando sale con codigo `0` solo si al menos un resultado viene de graph y no
hay `fallback_reason`. Si la proyeccion no esta `ready`, Neo4j falla o no hay
hits graph, imprime el reporte y sale con codigo `1`.

## Alcance

- Usa `RetrievalService` con `strategy=graph`.
- Reutiliza el provider dense configurado para generar el query embedding y
  producir seeds.
- Usa el `GraphRetriever` del `graph_store=neo4j` configurado.
- Conserva rehidratacion de citations desde Postgres y filtros existentes.

## Fuera de alcance

- No crea datos de fixture ni hace backfill automaticamente.
- No promueve `strategy=graph` como default.
- No reemplaza el futuro `m19-graph-live-evidence-report`; solo produce un
  smoke puntual para lectura live.
