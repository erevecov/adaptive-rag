# Propuesta M20 de dashboard de observability de chat

## Why

M17 cerro una superficie read-only de observability por API/CLI, pero el
frontend todavia no permite ver costo, latencia, errores y salud de sesiones
sin copiar JSON desde la CLI. M15/M16 ya dejaron una app React operativa para
chat, historial y streaming; el siguiente bloque de producto debe convertir el
contrato M17 en una pantalla de operacion local-first.

M19 cerro graph live ops con decision `hold_default`: Neo4j sigue opt-in y no
hay evidencia live local suficiente para avanzar a rollout/defaults. Sin un
entorno Neo4j live y dataset controlado, conviene pausar graph rollout y usar
M20 para mejorar visibilidad del flujo de chat ya estable.

El layout seleccionado para M20 es un dashboard hibrido: resumen ejecutivo con
filtros arriba, tarjetas de salud/costo/latencia, paneles de breakdown y tablas
operativas para provider usage y sesiones recientes. La implementacion debe
empezar consumiendo `GET /projects/{project_id}/chat/observability/summary` y
los endpoints de historial existentes, no creando un sistema BI paralelo.

## What Changes

- Crear el change OpenSpec `m20-chat-observability-dashboard-plan`.
- Modificar `chat-observability` para declarar el consumo dashboard-ready del
  resumen M17, manteniendo el endpoint read-only y backward-compatible.
- Modificar `chat-frontend` para declarar una vista read-only de observability
  dentro del frontend existente.
- Definir una secuencia M20 para:
  - agregar tipos y cliente frontend del resumen de observability;
  - construir una vista de dashboard con filtros y metric cards;
  - renderizar breakdowns y tablas desde `provider_usage.groups`, errores,
    status de sesiones y sesiones recientes;
  - cubrir estados loading/empty/error sin exponer secretos ni mensajes
    completos;
  - validar frontend, Python/OpenSpec y archivar el change al cierre.
- Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con M20
  activo.

## Capacidades

### Capacidades nuevas

- Ninguna.

### Capacidades modificadas

- `chat-observability`
- `chat-frontend`

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Agrega una nota de arquitectura para M20.
- Actualiza docs de progreso/roadmap.
- Este PR de planificacion no cambia codigo productivo Python ni frontend.
- No agrega nuevas tablas, materialized views, OpenTelemetry, exporters
  hosted, replay, auth final, cambios de retrieval/rerank/providers ni cambios
  de defaults graph.
