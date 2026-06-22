# M19 Neo4j local/managed harness

Fecha: 2026-06-22.

## Decision

M19 agrega un smoke CLI opt-in para validar conectividad Neo4j live sin cambiar
defaults. `graph_store=disabled` sigue siendo el default y `strategy=dense`
sigue siendo el default de retrieval.

El smoke usa el contrato existente `GraphStore.health_check()`, que a su vez
ejecuta `driver.verify_connectivity()` solo cuando el usuario solicita
`graph_store=neo4j`. Esto mantiene CI y tests offline libres de Neo4j, Docker,
Aura y credenciales.

## Comando

```text
adaptive-rag graph neo4j-smoke
```

Salida JSON:

- `backend`
- `available`
- `status`
- `error_code`
- `uri_scheme`
- `uri_kind`

El comando no imprime host completo, username ni password. `uri_kind` distingue
`managed_encrypted` para `neo4j+s://...` y `local_or_self_managed` para
`neo4j://...`, `bolt://...` o `bolt+s://...`.

## Ruta local

La ruta local esperada es Neo4j Desktop o Docker con Bolt expuesto en `7687` y
HTTP/Browser en `7474`. Para el smoke, el valor tipico es:

```text
ADAPTIVE_RAG_GRAPH_STORE=neo4j
ADAPTIVE_RAG_NEO4J_URI=neo4j://localhost:7687
ADAPTIVE_RAG_NEO4J_USERNAME=neo4j
ADAPTIVE_RAG_NEO4J_PASSWORD=<local-password>
```

## Ruta managed

La ruta managed esperada usa una URI cifrada tipo:

```text
ADAPTIVE_RAG_GRAPH_STORE=neo4j
ADAPTIVE_RAG_NEO4J_URI=neo4j+s://<database>.databases.neo4j.io
ADAPTIVE_RAG_NEO4J_USERNAME=neo4j
ADAPTIVE_RAG_NEO4J_PASSWORD=<managed-password>
```

Los secretos deben venir de `.env` local o variables de entorno. No deben
commitearse ni copiarse a reportes.

## Validacion

El smoke cubre settings, creacion del driver y connectivity check. No materializa
grafo, no hace backfill/reindex y no ejecuta retrieval graph. Es un prerequisito
operativo para `m19-graph-backfill-reindex-ops`.
