# Propuesta M14 de lectura/historial de chat

## Why

M13 cerro el audit trail durable de chat: sesiones, mensajes, tool calls,
retrieval runs, retrieved chunks, citations y usage/cost ya quedan persistidos.
Sin embargo, esa informacion todavia no tiene una superficie publica para
consulta aislada por proyecto.

Antes de construir frontend, streaming SSE o dashboards, Adaptive RAG necesita
un contrato minimo y estable para leer sesiones historicas y depurar una corrida
conversacional desde API y CLI. Esa superficie debe apoyarse en el audit trail
existente sin re-ejecutar chat, sin cambiar ranking y sin introducir UI todavia.

## What Changes

- Crear el change OpenSpec `m14-chat-history-read-surface`.
- Agregar la capacidad `chat-history` para definir:
  - listado paginado de sesiones por proyecto;
  - detalle de una sesion con mensajes, tool calls, retrieval runs, retrieved
    chunks/citations y provider usage;
  - comandos CLI equivalentes para inspeccion local;
  - guarantees de aislamiento por `project_id` y respuestas sin secretos.
- Definir una secuencia M14 para:
  - ampliar repositories/read models de audit trail;
  - agregar schemas y endpoints HTTP read-only;
  - agregar comandos CLI `chat sessions list` y `chat sessions show`;
  - validar respuestas deterministas con SQLite y fakes existentes.
- Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con M14
  activo.

## Capacidades

### Capacidades nuevas

- `chat-history`

### Capacidades modificadas

- Ninguna.

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Agrega una nota de arquitectura para M14.
- Actualiza docs de progreso/roadmap.
- El change planifica endpoints/comandos read-only futuros, pero este PR de
  planificacion no los implementa.
- No cambia ranking, providers, rerank, datasets de eval, defaults de retrieval,
  streaming SSE, dashboards, frontend ni replay de sesiones.
