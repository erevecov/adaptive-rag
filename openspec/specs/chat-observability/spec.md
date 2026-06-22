# chat-observability Specification

## Purpose
Define la superficie read-only de observability de chat por proyecto: resumen
de sesiones, status, errores, provider usage, costo/usage y latencia usando el
audit trail durable existente, con contrato JSON equivalente para API y CLI.
## Requirements
### Requirement: Chat observability expone resumen read-only

El sistema MUST exponer una superficie read-only para resumir observability de
chat por proyecto usando el audit trail durable existente.

#### Scenario: Resumen usa datos del proyecto

- **WHEN** el cliente solicita el resumen de observability de un proyecto
- **THEN** el sistema calcula agregados usando solo sesiones y provider usage de
  ese proyecto
- **AND** no devuelve datos de otros proyectos
- **AND** no crea ni modifica sesiones, mensajes, tool calls, retrieval runs ni
  provider usage

#### Scenario: Resumen acepta filtros acotados

- **WHEN** el cliente envia `created_at_from`, `created_at_to` o `status`
- **THEN** el sistema aplica esos filtros de forma deterministica
- **AND** rechaza filtros invalidos con error estable
- **AND** sin filtros de fecha cubre todos los datos persistidos del proyecto

### Requirement: Resumen reporta volumen, status y errores

El sistema MUST resumir volumen de sesiones, status y errores sin exponer
mensajes completos de usuario o assistant.

#### Scenario: Sesiones se agrupan por status

- **WHEN** existen sesiones `running`, `succeeded` y `failed`
- **THEN** el resumen incluye total de sesiones y conteos por status
- **AND** los conteos respetan filtros de proyecto, status y fecha

#### Scenario: Errores se agrupan de forma segura

- **WHEN** existen sesiones o provider usage con errores
- **THEN** el resumen incluye conteos de errores por fuente
- **AND** puede incluir mensajes de error estables truncados y agregados por
  conteo
- **AND** no incluye API keys, raw provider payloads, prompts completos ni
  respuestas completas

### Requirement: Resumen reporta costo, usage y latencia de providers

El sistema MUST agregar provider usage por operation/provider/model y reportar
costos, tokens/unidades y latencias sin inventar datos ausentes.

#### Scenario: Usage se agrupa por operation provider y model

- **WHEN** existen provider usage records del proyecto
- **THEN** el resumen agrupa records por `operation`, `provider` y `model`
- **AND** cada grupo incluye record count, costo estimado conocido,
  tokens/unidades conocidas y latencia agregada

#### Scenario: Costos y tokens ausentes quedan visibles

- **WHEN** un provider usage record no tiene costo, tokens o unidades
- **THEN** el resumen no inventa valores
- **AND** incrementa conteos de datos ausentes cuando correspondan
- **AND** suma totales solo con valores conocidos

#### Scenario: Latencia se resume de forma portable

- **WHEN** existen latencias en provider usage, tool calls o retrieval runs
- **THEN** el resumen puede reportar count, min, avg, p50, p95 y max sobre los
  valores conocidos
- **AND** el calculo debe ser deterministico en tests locales sin depender de
  funciones SQL especificas de un motor

### Requirement: API y CLI exponen el mismo contrato

El sistema MUST exponer el resumen de observability por API y CLI con shape JSON
equivalente.

#### Scenario: API devuelve resumen de proyecto

- **WHEN** `GET /projects/{project_id}/chat/observability/summary` recibe una
  solicitud valida
- **THEN** retorna JSON estable con filtros aplicados, sesiones, provider usage,
  latencias y errores
- **AND** respeta aislamiento por proyecto

#### Scenario: CLI devuelve resumen equivalente

- **WHEN** `adaptive-rag chat observability summary --project-id <uuid>` se
  ejecuta
- **THEN** escribe JSON estable equivalente al endpoint HTTP
- **AND** acepta filtros de fecha y status equivalentes

### Requirement: M17 preserva alcance local-first

El sistema MUST mantener M17 enfocado en observability local-first y no
introducir superficies fuera de alcance.

#### Scenario: No hay dashboard avanzado ni exporters

- **WHEN** M17 queda implementado
- **THEN** no agrega dashboard avanzado ni frontend obligatorio
- **AND** no agrega OpenTelemetry, Langfuse ni exporters hosted
- **AND** no agrega nuevas tablas obligatorias
- **AND** no agrega replay, edit, delete, retention ni auth final
- **AND** no cambia retrieval, rerank, providers ni streaming

### Requirement: Chat observability supports a read-only frontend dashboard

The system MUST allow a frontend dashboard to consume chat observability
summaries without changing the read-only audit trail contract.

#### Scenario: Dashboard consumes the existing project summary

- **WHEN** the frontend requests
  `GET /projects/{project_id}/chat/observability/summary`
- **THEN** the system returns the existing stable summary fields for filters,
  sessions, provider usage and errors
- **AND** applies the same project, `created_at_from`, `created_at_to` and
  `status` filters as the API/CLI contract
- **AND** does not create or modify sessions, messages, tool calls, retrieval
  runs or provider usage

#### Scenario: Dashboard derivations stay faithful to source aggregates

- **WHEN** the dashboard renders metric cards, breakdowns or tables from the
  summary
- **THEN** labels and values MUST reflect the source aggregate they use
- **AND** the system MUST NOT represent per-group latency percentiles as a
  global percentile unless the backend exposes that global aggregate
- **AND** missing cost, token or latency data remains visible instead of being
  invented client-side

#### Scenario: Chart-friendly additions are backward-compatible

- **WHEN** a later M20 slice extends the summary for chart-friendly fields such
  as time buckets or global latency aggregates
- **THEN** existing response fields remain backward-compatible
- **AND** added fields are derived from existing chat audit tables for the same
  project and filters
- **AND** no new mandatory tables, materialized views, exporters hosted or
  telemetry services are required

#### Scenario: Dashboard summary stays safe

- **WHEN** the dashboard displays observability data
- **THEN** it may show aggregate counts, costs, latency summaries, statuses and
  backend-truncated error messages
- **AND** it MUST NOT expose full user messages, full assistant answers, raw
  provider payloads, prompts, API keys or secrets
