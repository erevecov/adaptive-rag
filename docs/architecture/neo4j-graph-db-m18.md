# M18 Neo4j graph DB decision

Estado: activo como plan de M18.

## Decision

M18 debe avanzar como decision tecnica y plan routeable para graph DB, no como
adapter live inicial. Neo4j es el candidato principal porque tiene ecosistema
maduro, drivers oficiales, ruta local y ruta managed Aura, pero debe compararse
contra FalkorDB, Memgraph, Kuzu y la opcion no-op antes de agregar dependencias
o servicios.

La decision recomendada es empezar por decision matrix y contrato `GraphStore`.
Postgres sigue siendo la fuente durable de verdad; cualquier graph DB es un
indice derivado, reconstruible y deshabilitado por default.

La decision matrix quedo completada en
`docs/architecture/graph-db-decision-matrix-m18.md`: Neo4j queda en `proceed`
como primer backend live opt-in; Memgraph y FalkorDB quedan en `hold`; Kuzu
queda en `no-go` para el backend routeable de M18; no-op queda como fallback si
evals futuras no justifican graph retrieval.

## Evidencia externa consultada

Context7 resolvio docs oficiales de Neo4j y se consultaron:

- `/neo4j/docs-drivers`: driver/connectivity. El driver Python usa
  `GraphDatabase.driver(uri, auth=...)` y `verify_connectivity()` para comprobar
  conectividad.
- `/neo4j/docs-aura`: ruta managed. AuraDB usa URI, username y password; las
  conexiones managed cifradas usan URI tipo `neo4j+s://...databases.neo4j.io`.

## Alcance recomendado

- Documentar decision matrix Neo4j vs FalkorDB, Memgraph, Kuzu y no-op.
- Definir `graph_store=disabled` como default y `graph_store=neo4j` como opt-in
  futuro.
- Definir contrato `GraphStore`, health checks, errores estables y fakes
  offline antes de Neo4j live.
- Mantener Postgres como fuente durable y graph DB como indice derivado.
- Requerir rutas local y managed documentadas antes de adapter live.
- Requerir evals versionadas antes de promover retrieval graph.

## Fuera de alcance

- Agregar dependencia `neo4j` o `graphdatascience`.
- Agregar Docker Compose, Neo4j Desktop config o Aura secrets.
- Agregar migrations, tablas, settings productivos o infra.
- Agregar adapter live, indexer, reindex jobs o route de retrieval graph.
- Cambiar defaults de retrieval, rerank, chat, streaming o observability.

## Secuencia

1. `m18-neo4j-graph-db-decision`: completo.
2. `m18-graph-db-decision-matrix`: completo.
3. `m18-graph-store-contract`: pendiente.
4. `m18-neo4j-adapter-and-health`: pendiente.
5. `m18-neo4j-indexer`: pendiente.
6. `m18-graph-retrieval-route`: pendiente.
7. `m18-evals-quality-gate`: pendiente.

## Criterio de cierre

M18 debe cerrar cuando haya una decision proceed/no-go documentada, contrato
routeable testeado, adapter/indexer/ruta opt-in implementados solo si la
decision procede, y evals comparativas contra dense baseline antes de cualquier
cambio de default.
