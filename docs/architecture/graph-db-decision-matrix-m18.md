# M18 graph DB decision matrix

Fecha: 2026-06-21.

## Decision

M18 debe avanzar con Neo4j como primer candidato live para `GraphStore`, pero el
siguiente slice sigue siendo contrato/fakes, no adapter live.

Decision por alternativa:

- Neo4j: `proceed` como primer backend graph DB opt-in.
- Memgraph: `hold` como alternativa Bolt/Cypher si Neo4j falla por costo,
  licencia u operacion.
- FalkorDB: `hold` como alternativa Redis/OpenCypher para una ruta GraphRAG
  posterior, no como primer backend.
- Kuzu: `no-go` para el backend routeable de M18; conservar solo como posible
  opcion local/offline de analisis.
- No-op: `reject` como decision principal de M18, pero mantener como fallback si
  evals posteriores no justifican retrieval graph.

La recomendacion concreta es que `m18-graph-store-contract` defina solo
`graph_store=disabled` y `graph_store=neo4j`. No debe agregar settings para
Memgraph, FalkorDB o Kuzu hasta que una decision posterior los promueva.

El contrato tambien debe permitir que Neo4j haya estado apagado o deshabilitado:
Postgres conserva la fuente canonica y el estado de readiness/backfill por
proyecto; cuando se habilita `graph_store=neo4j`, un backfill reconstruye la
proyeccion en Neo4j y retrieval graph espera hasta que el estado sea `ready`.

## Criterios

- Local setup: debe existir una ruta local reproducible para desarrollo.
- Managed setup: debe existir una ruta hosted/managed para validar despliegue
  fuera del equipo local.
- Python integration: debe poder integrarse con un runtime Python sin acoplar
  tests unitarios a un servicio live.
- Query language: debe soportar consultas de grafo expresivas y suficientemente
  portables para retrieval graph.
- Licenciamiento: debe dejar claro si el backend impone licencias comerciales,
  copyleft o restricciones de servicio antes de adoptarlo en runtime.
- Operational fit: debe poder fallar con errores estables, health checks y sin
  secretos en logs/responses.
- Retrieval fit: debe preservar project isolation, metadata filters, citations,
  audit trail y fallback a dense retrieval.

## Matriz resumida

| Alternativa | Local | Managed | Python | Query | Licencia/terms | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| Neo4j | Docker/Desktop viable | Aura viable | Driver oficial | Cypher | CE GPLv3; EE/Aura commercial terms | `proceed` |
| Memgraph | Docker viable | Memgraph Cloud viable | Neo4j driver / pymgclient | Cypher/Bolt compatible | Community bajo BSL; Enterprise/Cloud terms | `hold` |
| FalkorDB | Docker viable | FalkorDB Cloud viable | Cliente propio | OpenCypher subset | Core SSPLv1; commercial option | `hold` |
| Kuzu | Embedded viable | No cubre servicio managed | Paquete embedded | Cypher | MIT | `no-go` para M18 |
| No-op | N/A | N/A | Sin cambios | N/A | N/A | fallback solamente |

## Neo4j

Decision: `proceed`.

Fortalezas:

- Tiene driver oficial de Python y la conectividad se puede comprobar con
  `verify_connectivity()`.
- Cubre local y managed: `neo4j://localhost` o `bolt://localhost` para local y
  `neo4j+s://...databases.neo4j.io` para Aura/managed cifrado.
- Aura entrega una ruta hosted con URI, username y password por instancia.
- Cypher es el baseline natural para modelar traversal de documentos, chunks,
  sources, entities y relaciones.
- Encaja con el requisito de health checks antes de uso online.
- CE/EE/Aura tienen terminos distintos, pero el PR actual no agrega
  distribucion, runtime ni dependencia Neo4j.

Riesgos:

- Agrega un segundo servicio operacional.
- Aura/local pueden diferir en TLS, routing, credenciales y errores.
- Si no hay reindex idempotente, el grafo puede divergir de Postgres.
- Puede aumentar latencia/costo si entra en retrieval online sin gates.

Condiciones:

- Postgres sigue siendo la fuente durable.
- El grafo es indice derivado y reconstruible.
- `graph_store=disabled` sigue siendo default.
- `graph_store=neo4j` solo se usa opt-in.
- No se promueve retrieval graph sin evals versionadas.

## Memgraph

Decision: `hold`.

Fortalezas:

- Documenta compatibilidad con Cypher y Bolt para migraciones desde Neo4j.
- Tiene ruta local y Memgraph Cloud.
- Puede usarse con el driver Neo4j en Python para casos compatibles, y tambien
  existe `pymgclient`.
- Es una alternativa razonable si Neo4j falla por costo, licencia u operacion.
- Community Edition usa Business Source License; Enterprise/Cloud requieren
  revisar terminos antes de runtime productivo.

Riesgos:

- La compatibilidad con Neo4j debe verificarse con las queries reales del
  contrato, no asumirse por protocolo.
- Memgraph Cloud tiene detalles operacionales propios, por ejemplo IP nueva al
  pausar/reanudar proyectos.
- Agregarlo ahora ampliaria settings, tests y soporte antes de saber si Neo4j
  cubre el caso.

Condicion para promover:

- Solo reconsiderar si `GraphStore` queda suficientemente desacoplado y Neo4j
  falla una condicion critica antes de adapter/indexer.

## FalkorDB

Decision: `hold`.

Fortalezas:

- Documenta OpenCypher, Docker y una ruta FalkorDB Cloud.
- Tiene Python client propio y una variante lite/embedded para algunos usos.
- Su posicionamiento GraphRAG puede ser util en una comparacion futura.
- El core usa SSPLv1, con opcion comercial para escenarios donde SSPL no encaje.

Riesgos:

- Su semantica no es una equivalencia Neo4j directa; implementa un subconjunto
  de OpenCypher con extensiones propias.
- Su operacion esta mas cerca de Redis/module y comandos `GRAPH.*`, lo que
  cambiaria el contrato del adapter.
- Puede introducir decisiones de protocolo y deployment distintas antes de que
  el proyecto tenga un contrato `GraphStore` estable.

Condicion para promover:

- Reabrir si Neo4j/Memgraph no cumplen latencia/costo o si una suite GraphRAG
  muestra una ventaja concreta de FalkorDB.

## Kuzu

Decision: `no-go` para el backend routeable de M18.

Fortalezas:

- Embedded/in-process, con integracion Python y Cypher.
- No requiere administrar un servicio local para experimentos.
- Puede ser util para analisis offline o fixtures locales.
- Licencia MIT permisiva.

Riesgos:

- No cubre el requisito M18 de una ruta local-service y managed equivalente.
- Su modelo embedded no prueba health checks, credenciales, routing ni errores
  de servicio remoto.
- El repositorio/documentacion actual senalan transicion del proyecto y recursos
  movidos a GitHub, lo que aumenta el riesgo para adoptarlo como backend
  operativo principal.

Condicion para promover:

- Mantener como opcion de investigacion local/offline, no como
  `graph_store=<backend>` en M18.

## No-op

Decision: fallback solamente.

Fortalezas:

- Mantiene el stack simple.
- Evita costo, latencia y operacion nuevos.
- Dense/rerank siguen siendo el baseline probado.

Riesgos:

- No prueba si relaciones estructurales pueden mejorar casos de retrieval que
  dense/rerank no resuelven.
- No reduce incertidumbre sobre graph retrieval.

Condicion:

- Si evals futuras no muestran mejora sin regresiones criticas, M18 debe cerrar
  dejando `graph_store=disabled` como unico default efectivo.

## Implicacion para el siguiente slice

`m18-graph-store-contract` debe hacer lo minimo:

- definir enum/config para `disabled` y `neo4j`;
- definir interfaz `GraphStore` sin importar el driver Neo4j todavia;
- definir estado de proyeccion por proyecto en Postgres: `disabled`,
  `pending_backfill`, `indexing`, `ready`, `stale` y `failed`;
- definir watermark/source version, schema/extractor version, `last_indexed_at`
  y error code estable para backfill/reindex;
- definir errores estables: misconfigured, unavailable y query failure;
- definir `health_check()` como contrato, pero con fake offline primero;
- definir `backfill_project_graph(...)` o un job equivalente que reconstruya
  Neo4j desde Postgres de forma idempotente por `project_id`;
- definir fakes deterministas que cubran tests sin Docker, Aura ni credenciales;
- preservar fallback dense cuando graph store este disabled, unavailable,
  `pending_backfill`, `indexing`, `stale` o `failed`;
- no cambiar API/CLI productivos.

No hace falta almacenar todos los nodos/aristas temporales en Postgres si se
pueden derivar de tablas canonicas. Si luego agregamos extraccion costosa de
entidades o relaciones, esos graph facts si deben persistirse en Postgres con
version/hash para que el backfill hacia Neo4j no dependa de repetir trabajo
externo o no determinista.

## Fuentes consultadas

- Context7: `/websites/neo4j`, `/neo4j/docs-drivers`, `/neo4j/docs-aura`,
  `/websites/memgraph`, `/kuzudb/docs`, `/falkordb/docs`.
- Neo4j Python driver:
  https://neo4j.com/docs/python-manual/current/connect/
- Neo4j Aura connection:
  https://neo4j.com/docs/aura/getting-started/connect-instance/
- Neo4j license/editions:
  https://github.com/neo4j/neo4j
- Memgraph Neo4j migration compatibility:
  https://memgraph.com/docs/data-migration/migrate-from-neo4j
- Memgraph Python client docs:
  https://memgraph.com/docs/client-libraries/python
- Memgraph Cloud:
  https://memgraph.com/docs/getting-started/install-memgraph/memgraph-cloud
- Memgraph legal terms:
  https://memgraph.com/legal
- FalkorDB docs:
  https://docs.falkordb.com/
- FalkorDB Cypher support:
  https://docs.falkordb.com/cypher/cypher-support.html
- FalkorDB license:
  https://docs.falkordb.com/References/license.html
- Kuzu docs:
  https://kuzudb.github.io/docs
- Kuzu repository:
  https://github.com/kuzudb/kuzu
