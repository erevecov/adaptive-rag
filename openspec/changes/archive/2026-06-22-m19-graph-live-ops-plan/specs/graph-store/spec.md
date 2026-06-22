## ADDED Requirements

### Requirement: Graph live ops requiere evidencia operacional

El sistema MUST mantener graph retrieval como opt-in hasta que exista evidencia
operacional con Neo4j live.

#### Scenario: M19 no cambia defaults

- **WHEN** se abre el milestone de graph live ops
- **THEN** `graph_store=disabled` sigue siendo el default de configuracion
- **AND** `strategy=dense` sigue siendo el default de retrieval
- **AND** cualquier uso de Neo4j live requiere opt-in explicito

#### Scenario: Setup live separa local y managed

- **WHEN** se documenta o ejecuta un smoke de Neo4j live
- **THEN** existe una ruta local verificable con Docker o Neo4j Desktop
- **AND** existe una ruta managed con URI cifrada tipo `neo4j+s://...`
- **AND** los errores de configuracion o conectividad se reportan con codigos
  estables sin exponer secretos

### Requirement: Backfill y reindex graph son operaciones idempotentes

El sistema MUST exponer operaciones de backfill/reindex de graph store acotadas
por proyecto antes de evaluar promocion de graph retrieval.

#### Scenario: Backfill transiciona readiness

- **WHEN** se ejecuta backfill de una proyeccion graph para un `project_id`
- **THEN** la proyeccion pasa por `pending_backfill` o `indexing`
- **AND** termina en `ready` si la materializacion completa con exito
- **AND** termina en `failed` con error code estable si Neo4j o el loader fallan

#### Scenario: Reindex stale conserva aislamiento

- **WHEN** una proyeccion esta `stale` y se solicita reindex
- **THEN** el sistema reconstruye nodos y relaciones solo para ese `project_id`
- **AND** la operacion es idempotente si se repite
- **AND** no mezcla datos, filtros ni citations entre proyectos

### Requirement: Evidence report mide calidad y operacion live

El sistema MUST producir evidencia comparativa live antes de considerar cambios
de default.

#### Scenario: Reporte live compara dense contra graph

- **WHEN** se ejecuta un reporte de evidencia con Neo4j live
- **THEN** incluye dense baseline y resultados `strategy=graph`
- **AND** reporta hit rate, best-rank delta, mejoras, empates y regresiones
- **AND** reporta metadata filter coverage y citation coverage

#### Scenario: Reporte live incluye metricas operativas

- **WHEN** se serializa el reporte de evidencia graph live
- **THEN** incluye latencia de retrieval graph
- **AND** incluye duracion de backfill o reindex
- **AND** incluye fallback counts y error codes estables
- **AND** separa costo provider de costo operacional graph declarado

### Requirement: Decision gate de M19 es conservador

El sistema MUST cerrar M19 con una decision que no promueve graph como default.

#### Scenario: Gate conserva dense default

- **WHEN** M19 evalua la evidencia graph live
- **THEN** la decision es `hold_default`, `limited_experiment` o
  `no_go_promotion`
- **AND** `promote_default` queda fuera de alcance de M19
- **AND** cualquier promocion de default requiere un milestone posterior con
  rollout, rollback y observability definidos
