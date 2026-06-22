# M18 Neo4j adapter and health

Fecha: 2026-06-22.

## Decision

`m18-neo4j-adapter-and-health` agrega el primer adapter live de graph store, pero
lo mantiene estrictamente opt-in. `graph_store=disabled` sigue siendo el default;
`graph_store=neo4j` requiere URI, username y password desde settings.

Context7 resolvio `/neo4j/neo4j-python-driver` para validar el API actual del
driver. El adapter usa `GraphDatabase.driver(uri, auth=(username, password))` y
ejecuta `verify_connectivity()` solo dentro de `health_check()`.

## Implementacion

- Dependencia runtime: `neo4j>=6.0`, resuelta como `neo4j==6.2.0`.
- `Neo4jGraphStore` implementa el contrato `GraphStore` para health/lifecycle.
- `get_graph_store(...)` devuelve `DisabledGraphStore` por default y
  `Neo4jGraphStore` solo cuando `graph_store=neo4j`.
- La factory recibe un `driver_factory` inyectable para tests sin red.
- `health_check()` mapea errores del driver a `GraphStoreHealth`:
  - auth invalida: `graph_store_misconfigured`;
  - servicio/driver no disponible: `graph_store_unavailable`;
  - error Neo4j generico: `graph_store_query_failed`.
- Los mensajes externos no incluyen URI completa con credenciales ni password.

## Rutas soportadas

- Local: URI tipo `neo4j://localhost:7687` o `bolt://localhost:7687` con auth.
- Managed/Aura: URI cifrada tipo `neo4j+s://...databases.neo4j.io` con username
  y password desde settings.

## Fuera de alcance

- Docker Compose, Neo4j Desktop config o Aura secrets.
- Indexer y reindex jobs.
- Materializacion de nodos/relaciones.
- Retrieval graph online.
- Cambios de defaults de retrieval.

## Siguiente paso

`m18-neo4j-indexer` ya usa este adapter para materializar el indice derivado
desde Postgres de forma idempotente por `project_id`. El siguiente paso es
`m18-graph-retrieval-route`, todavia sin cambiar defaults.
