# Delta for graph-store

## ADDED Requirements

### Requirement: Graph DB decision define alcance routeable

El sistema MUST tratar la adopcion de graph DB como una decision explicita,
routeable y reversible antes de integrar un adapter live.

#### Scenario: Decision matrix compara alternativas

- **WHEN** se planifica graph DB para retrieval graph
- **THEN** la decision matrix compara Neo4j con alternativas locales/managed
  relevantes
- **AND** incluye al menos FalkorDB, Memgraph, Kuzu y la opcion no-op
- **AND** documenta tradeoffs de setup local, managed, drivers, query language,
  costo operativo, madurez, testability y fit con retrieval

#### Scenario: Graph store queda deshabilitado por default

- **WHEN** se define configuracion para graph DB
- **THEN** `graph_store=disabled` es el default
- **AND** cualquier backend graph live requiere opt-in explicito
- **AND** el default de retrieval no cambia hasta pasar evals versionadas

### Requirement: Graph store es indice derivado y reconstruible

El sistema MUST mantener Postgres como fuente durable principal y tratar graph
DB como indice derivado reconstruible.

#### Scenario: Postgres sigue siendo fuente de verdad

- **WHEN** se materializan nodos o relaciones en graph DB
- **THEN** esos datos se derivan de proyectos, sources, documents, document
  versions, chunks y metadata persistidos en Postgres
- **AND** el sistema puede reconstruir el grafo desde Postgres
- **AND** graph DB no contiene la unica copia durable de datos primarios

#### Scenario: Graph store puede estar deshabilitado sin perder rebuild

- **WHEN** `graph_store=disabled` durante ingestion, actualizacion o borrado de
  datos
- **THEN** la operacion persiste la fuente canonica necesaria en Postgres
- **AND** no requiere escribir en Neo4j ni en otro backend graph live
- **AND** una habilitacion posterior de graph store puede reconstruir el grafo
  mediante backfill desde Postgres

#### Scenario: Operaciones preservan aislamiento por proyecto

- **WHEN** se indexa, borra, reindexa o consulta graph DB
- **THEN** la operacion queda acotada por `project_id`
- **AND** no mezcla nodos, relaciones, filtros ni citations entre proyectos

### Requirement: Graph projection mantiene readiness en Postgres

El sistema MUST registrar en Postgres el estado de la proyeccion graph por
proyecto antes de usar retrieval graph.

#### Scenario: Habilitar graph store agenda backfill

- **WHEN** un proyecto habilita un backend graph live despues de estar
  deshabilitado
- **THEN** el estado de la proyeccion graph queda en `pending_backfill` o
  `indexing`
- **AND** el backfill materializa nodos y relaciones desde datos canonicos en
  Postgres
- **AND** retrieval graph no se usa para ese proyecto hasta que el estado sea
  `ready`

#### Scenario: Readiness controla fallback

- **WHEN** una consulta intenta usar retrieval graph y la proyeccion esta en
  `disabled`, `pending_backfill`, `indexing`, `stale` o `failed`
- **THEN** el sistema usa fallback a dense retrieval
- **AND** registra una razon estable de fallback en audit trail cuando graph
  retrieval fue solicitado
- **AND** no bloquea chat ni retrieval baseline por falta de graph readiness

#### Scenario: Watermark detecta stale projection

- **WHEN** cambian documents, document versions, chunks, metadata, schema de
  proyeccion o version de extractor despues del ultimo backfill
- **THEN** el estado de la proyeccion queda `stale` o `pending_backfill`
- **AND** Postgres conserva un watermark o version que permite decidir que debe
  reindexarse
- **AND** el backfill posterior es idempotente por `project_id`

### Requirement: Graph store expone contrato testeable

El sistema MUST definir un contrato de graph store antes de acoplarse a Neo4j
live.

#### Scenario: Contrato soporta health checks y errores estables

- **WHEN** una implementacion de graph store se inicializa o se usa
- **THEN** expone un health check de conectividad
- **AND** reporta errores estables para configuracion invalida, servicio no
  disponible y fallos de query
- **AND** no expone secretos en errores, logs ni responses

#### Scenario: Fakes offline cubren tests

- **WHEN** los tests unitarios o de contrato corren sin Neo4j live
- **THEN** usan fakes deterministas del contrato graph store
- **AND** no requieren Docker, Neo4j Desktop, Aura ni credenciales hosted

### Requirement: Neo4j live requiere setup local y managed documentado

El sistema MUST documentar una ruta local y una ruta managed antes de depender
de Neo4j live.

#### Scenario: Ruta local es verificable

- **WHEN** se habilita `graph_store=neo4j` en entorno local
- **THEN** existe una ruta documentada con Docker o Neo4j Desktop
- **AND** el adapter puede verificar conectividad con URI y auth
- **AND** fallos de conexion producen errores estables

#### Scenario: Ruta managed usa conexion cifrada

- **WHEN** se usa Neo4j Aura u otra ruta managed equivalente
- **THEN** la configuracion acepta URI, username y password desde settings
- **AND** soporta URIs cifradas tipo `neo4j+s://...`
- **AND** no persiste ni imprime credenciales

### Requirement: Retrieval graph preserva contrato existente

El sistema MUST preservar contratos existentes de retrieval cuando graph DB se
usa como ruta opt-in.

#### Scenario: Retrieval graph respeta filtros y citations

- **WHEN** una consulta usa retrieval graph
- **THEN** respeta aislamiento por proyecto y metadata filters
- **AND** devuelve citations compatibles con la superficie de retrieval actual
- **AND** registra audit trail de estrategia y fallos

#### Scenario: Promotion requiere evals

- **WHEN** se considera promover retrieval graph como default
- **THEN** debe existir comparacion contra dense baseline en suites versionadas
- **AND** la comparacion cubre calidad, costo, latencia, filtros y citations
- **AND** no puede haber regresiones criticas antes de cambiar defaults
