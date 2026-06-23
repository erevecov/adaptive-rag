# Delta for ingestion-pipeline

## MODIFIED Requirements

### Requirement: Ingestion pipeline mantiene aislamiento por proyecto

El sistema MUST rechazar jobs `ingest_source` cuyo payload intente cargar una
source que no pertenece al `project_id` del job leaseado.

#### Scenario: Source de otro proyecto bloquea el job

- **WHEN** un job de un proyecto referencia una source de otro proyecto
- **THEN** el pipeline no crea documents ni document versions
- **AND** marca el job como `blocked`
- **AND** registra el evento `blocked` con el mismo `project_id` del job
- **AND** devuelve un resultado observable que identifica el job bloqueado y el
  error
