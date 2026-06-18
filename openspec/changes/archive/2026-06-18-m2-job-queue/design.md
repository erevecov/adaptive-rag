# Diseno M2 de job queue

## Contexto

M2 necesita una cola persistente antes de ingestion. La capa debe permitir que futuros workers tomen trabajos de forma auditable sin mezclar todavia fetch policy, parsing ni chunking.

## Objetivos

- Persistir jobs por proyecto con `job_type`, `payload_json`, prioridad, estado, intentos y lease.
- Registrar eventos inmutables por job para auditoria y diagnostico.
- Permitir retries controlados por `attempts`, `max_attempts` y `run_after`.
- Permitir estados terminales o manuales: `succeeded`, `blocked` y `dead_letter`.
- Mantener el caller como dueno de la transaccion; repositories usan `flush()` pero no `commit()`.

## No objetivos

- No ejecutar jobs.
- No crear workers, timers, background tasks ni APIs.
- No definir payloads especificos de ingestion.
- No implementar URL fetch policy ni parsing.
- No resolver concurrencia distribuida completa; solo se prepara `SELECT ... FOR UPDATE SKIP LOCKED` para Postgres y comportamiento determinista en tests.

## Decisiones

### D1. Dos tablas: jobs y job_events

`jobs` guarda el estado actual. `job_events` guarda el historial append-only con `event_type`, mensaje y metadata opcional. `project_id` se guarda tambien en events para consultas aisladas sin joins obligatorios.

### D2. Estados simples y auditables

Los estados validos de job son `queued`, `running`, `succeeded`, `blocked` y `dead_letter`. Los fallos intermedios no son estado estable: se registran como eventos y el job vuelve a `queued` si quedan intentos.

### D3. Leasing dentro del repository

`lease_next()` selecciona jobs `queued` con `run_after <= now`, ordenados por prioridad descendente y antiguedad. Al leasear, incrementa `attempts`, escribe `locked_by`, `locked_until`, cambia a `running` y agrega evento `leased`.

### D4. Retries no duermen dentro del proceso

`fail()` no espera ni reintenta en memoria. Si quedan intentos, vuelve el job a `queued` y actualiza `run_after`. Si no quedan intentos, lo mueve a `dead_letter`.

## Riesgos y mitigaciones

- Riesgo: sobrediseno de scheduler. Mitigacion: solo persistencia y leasing; ejecucion real queda fuera.
- Riesgo: locks concurrentes no se prueban bien en SQLite. Mitigacion: unit tests cubren contrato determinista y migracion Postgres valida indices/constraints.
- Riesgo: estados ambiguos. Mitigacion: checks DB y constantes de modelo/repository mantienen el vocabulario cerrado.

## Despliegue

1. Agregar OpenSpec change.
2. Escribir tests rojos de modelos y repository.
3. Agregar modelos y migracion Alembic.
4. Implementar `JobRepository`.
5. Validar quality gate y archivar el change.

