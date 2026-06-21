# Propuesta M16 de streaming SSE para chat

## Why

M15 dejo una UI operativa para enviar preguntas con `POST /chat` y revisar
historial read-only. El siguiente riesgo de experiencia no es dashboard ni
replay: las respuestas largas siguen siendo bloqueantes, sin progreso visible
ni eventos intermedios de retrieval/tool calling.

Adaptive RAG necesita una superficie streaming que preserve los contratos ya
cerrados de chat, audit trail e historial, mientras permite al frontend mostrar
respuesta parcial y progreso sin esperar el JSON final. La opcion recomendada
es Server-Sent Events sobre un endpoint `POST`, porque el flujo de chat ya
necesita body JSON con `message`, `retrieval_limit` y filtros; usar un
`EventSource` nativo con `GET` forzaria parametros sensibles o incomodos en la
URL.

La documentacion actual de FastAPI consultada via `ctx7` confirma que
`StreamingResponse` puede emitir `text/event-stream` con generadores async y
que FastAPI 0.137.1 disponible en el repo expone `fastapi.sse.EventSourceResponse`.
M16 debe fijar el contrato antes de tocar runners, API y frontend.

## What Changes

- Crear el change OpenSpec `m16-chat-streaming-sse`.
- Agregar la capacidad `chat-streaming` para definir:
  - endpoint HTTP streaming para chat por proyecto;
  - formato SSE versionado y testeable;
  - eventos minimos de session, tool calls, answer deltas, final response,
    errores y heartbeat;
  - persistencia compatible con el audit trail durable;
  - cliente frontend con parser de streaming y fallback al flujo no streaming.
- Definir una secuencia M16 para:
  - introducir tipos/eventos de streaming sin romper `ChatService.respond()`;
  - agregar endpoint FastAPI SSE sobre `POST /projects/{project_id}/chat/stream`;
  - adaptar frontend para consumir SSE via `fetch` streaming;
  - cubrir cancelacion, fallback, error states y QA local;
  - validar y archivar el change.
- Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con M16
  activo.

## Capacidades

### Capacidades nuevas

- `chat-streaming`

### Capacidades modificadas

- Ninguna.

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Agrega una nota de arquitectura para M16.
- Actualiza docs de progreso/roadmap.
- Este PR de planificacion no cambia codigo productivo Python ni frontend.
- No cambia ranking, retrieval, rerank, providers por defecto, historial
  read-only, dashboards, replay, WebSockets ni auth final.
