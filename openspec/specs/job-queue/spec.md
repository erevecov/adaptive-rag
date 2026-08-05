# job-queue Specification

## Purpose

Definir el contrato de cola persistente de jobs para Adaptive RAG: trabajo
asincronico aislado por proyecto, eventos auditables, retries y leasing de
workers.
## Requirements
### Requirement: Jobs persisten trabajo asincronico por proyecto

El sistema MUST persistir jobs aislados por `project_id` con tipo, payload, prioridad, estado, intentos, limites de retry y lease opcional.

#### Scenario: Job nuevo queda queued

- **WHEN** se crea un job para un proyecto
- **THEN** el job queda con `status = queued`
- **AND** `attempts = 0`
- **AND** `max_attempts` es positivo

#### Scenario: Estados invalidos son rechazados

- **WHEN** se intenta persistir un job con estado fuera de `queued`, `running`, `succeeded`, `blocked` o `dead_letter`
- **THEN** la base de datos rechaza la fila

### Requirement: Job events registran auditoria append-only

El sistema MUST persistir eventos por job con `project_id`, `event_type`, mensaje opcional, metadata opcional y timestamp.

#### Scenario: Crear job registra evento created

- **WHEN** el repository crea un job
- **THEN** tambien agrega un evento `created` para ese job

#### Scenario: Eventos se listan por job y proyecto

- **WHEN** un job tiene multiples eventos
- **THEN** el repository los devuelve ordenados por creacion
- **AND** no devuelve eventos si el `project_id` no corresponde

### Requirement: Leasing asigna jobs disponibles a workers

El sistema MUST permitir que un worker leasee el siguiente job disponible sin hacer `commit()` implicito.

#### Scenario: Lease toma el job queued mas prioritario y vencido

- **WHEN** existen jobs `queued` con `run_after <= now`
- **THEN** `lease_next` devuelve el job con mayor prioridad y mayor antiguedad
- **AND** lo cambia a `running`
- **AND** incrementa `attempts`
- **AND** guarda `locked_by` y `locked_until`

#### Scenario: Jobs futuros o de otro proyecto no se leasean

- **WHEN** un job tiene `run_after > now` o pertenece a otro proyecto
- **THEN** `lease_next` no lo devuelve

### Requirement: Retry, blocked y dead-letter son transiciones explicitas

El sistema MUST proveer transiciones de repository para completar, reintentar, bloquear y enviar jobs a `dead_letter`.

#### Scenario: Falla con intentos disponibles vuelve a queued

- **WHEN** un job `running` falla y `attempts < max_attempts`
- **THEN** el job vuelve a `queued`
- **AND** `run_after` refleja el proximo intento
- **AND** el lease queda limpio

#### Scenario: Falla sin intentos disponibles queda dead_letter

- **WHEN** un job `running` falla y `attempts >= max_attempts`
- **THEN** el job queda con `status = dead_letter`
- **AND** el lease queda limpio

#### Scenario: Leases vencidos se liberan

- **WHEN** un job `running` tiene `locked_until <= now`
- **THEN** el repository puede devolverlo a `queued` y limpiar el lease

### Requirement: Jobs can be listed and manually requeued

The job repository MUST support public ingestion operations without forcing
callers to write SQL.

#### Scenario: Jobs are listed deterministically

- **WHEN** API or CLI lists jobs for a project
- **THEN** `JobRepository` returns project-scoped jobs ordered by creation time
  and id
- **AND** optional filters can narrow by status and job type

#### Scenario: Blocked or dead-letter jobs are requeued manually

- **WHEN** API or CLI retries a `blocked` or `dead_letter` job
- **THEN** `JobRepository` moves it to `queued`
- **AND** clears `locked_by`, `locked_until` and `last_error`
- **AND** appends a `retried` event

### Requirement: Worker can lease ingestion-family job types

The job repository/worker MUST support leasing the next ready job among a
declared set of job types so ingestion and indexing share one public worker loop.

#### Scenario: Lease prefers highest priority ready family job

- **WHEN** a project has queued `ingest_source` and `index_document_version` jobs
  ready to run
- **AND** the worker leases the next job for the ingestion family
- **THEN** selection uses existing priority / run_after / created_at ordering
- **AND** jobs of unrelated types (for example graph jobs) are not leased by
  that family worker

### Requirement: Worker recovers expired leases before leasing

The public ingestion-family worker MUST release expired running leases for the
project before selecting the next job.

#### Scenario: Expired running job becomes leaseable again

- **WHEN** a job is `running` with `locked_until <= now`
- **AND** a worker runs the next ingestion-family cycle for that project
- **THEN** the system releases the expired lease back to `queued`
- **AND** appends a `released` event
- **AND** the job may be leased again by a subsequent worker cycle

### Requirement: Unexpected job failures use fail with backoff

The worker MUST route unexpected exceptions through `JobRepository.fail()` so
retries and dead-letter are real, not stuck `running` rows.

#### Scenario: Unexpected error requeues with backoff while attempts remain

- **WHEN** a leased job raises an unexpected exception and `attempts < max_attempts`
- **THEN** the job returns to `queued` via `fail()`
- **AND** `run_after` is set in the future according to backoff
- **AND** `last_error` stores the error message
- **AND** a `failed_attempt` event is recorded

#### Scenario: Unexpected error dead-letters when attempts are exhausted

- **WHEN** a leased job raises an unexpected exception and `attempts >= max_attempts`
- **THEN** the job status becomes `dead_letter`
- **AND** a `dead_lettered` event is recorded
- **AND** the job is not left in `running`

