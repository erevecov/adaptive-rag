# Propuesta M13 de audit trail de chat

## Why

M12 cerro la expansion de evidencia de retrieval sin justificar nuevos
algoritmos, presets ni defaults. El siguiente riesgo relevante ya no esta en
ranking: las respuestas de chat, tool calls, retrieval runs, citations y usage
de providers existen como payloads transitorios, pero no quedan unidos en un
audit trail durable.

Antes de agregar streaming SSE, dashboards, historial de sesiones o
LLM-as-judge, Adaptive RAG necesita persistir una corrida conversacional minima
para poder reproducir que contexto se recupero, que tools se llamaron, que
respuesta se emitio, que costo/usage produjo y como fallo cuando hubo error.

## What Changes

- Crear el change OpenSpec `m13-chat-audit-trail`.
- Agregar la capacidad `chat-audit-trail` para definir persistencia durable de:
  - sesiones de chat;
  - mensajes de usuario/assistant;
  - tool calls y errores;
  - retrieval runs asociados a chat;
  - chunks/citations recuperados;
  - provider usage vinculado a sesion, job o eval cuando aplique.
- Definir una secuencia M13 para:
  - agregar schema Alembic y modelos SQLAlchemy;
  - agregar repositories de audit trail;
  - integrar persistencia en `ChatService` sin cambiar retrieval productivo;
  - mantener API/CLI compatibles, con metadata minima de sesion cuando sea
    necesario;
  - validar consistencia del audit trail con fakes deterministas.
- Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con M13
  activo.

## Capacidades

### Capacidades nuevas

- `chat-audit-trail`

### Capacidades modificadas

- Ninguna.

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Agrega una nota de arquitectura para M13.
- Actualiza docs de progreso/roadmap.
- El change planifica migraciones Alembic y codigo productivo futuros, pero este
  PR de planificacion no los implementa.
- No cambia ranking, providers, rerank, datasets de eval, defaults de retrieval,
  streaming SSE, dashboards ni historial/listado de sesiones.
