# Propuesta M17 de observability de chat y costo-latencia

## Why

M16 dejo chat streaming operativo y persistido sobre audit trail durable. El
siguiente riesgo operativo no es replay ni auth final: todavia falta una
superficie pequena para responder preguntas basicas de operacion local-first:
cuantas sesiones corrieron, cuanto costaron, que latencia tuvieron, que
operaciones de provider dominaron el gasto y donde fallaron.

Adaptive RAG ya guarda `chat_sessions`, `tool_calls`, `retrieval_runs` y
`provider_usage`. M17 debe convertir esos datos en resumen reproducible para
API y CLI antes de construir una UI o dashboard. La opcion recomendada es
read-only, sin tablas nuevas inicialmente, para mantener bajo el blast radius y
producir evidencia util para la release v1.0 de portafolio.

## What Changes

- Crear el change OpenSpec `m17-chat-observability`.
- Agregar la capacidad `chat-observability` para definir:
  - resumen read-only por proyecto;
  - agregados de sesiones por status;
  - agregados de usage/costo por operation/provider/model;
  - agregados de latencia y errores desde audit trail y provider usage;
  - superficies equivalentes API y CLI.
- Definir una secuencia M17 para:
  - agregar read models/repository queries portables;
  - exponer endpoint HTTP de resumen;
  - exponer comando CLI equivalente;
  - validar gates y archivar el change.
- Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con M17
  activo.

## Capacidades

### Capacidades nuevas

- `chat-observability`

### Capacidades modificadas

- Ninguna.

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Agrega una nota de arquitectura para M17.
- Actualiza docs de progreso/roadmap.
- Este PR de planificacion no cambia codigo productivo Python ni frontend.
- No agrega dashboards avanzados, OpenTelemetry, nuevas tablas, frontend,
  replay, auth final ni cambios de retrieval/rerank/providers.
