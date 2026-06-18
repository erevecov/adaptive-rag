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
