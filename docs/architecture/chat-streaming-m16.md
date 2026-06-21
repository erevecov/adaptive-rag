# M16 Chat streaming SSE

Estado: completo el 2026-06-21.

## Decision

M16 cerro una superficie de streaming para chat sobre los contratos ya cerrados:
`POST /chat` de M5, audit trail durable de M13, historial read-only de M14 y
frontend operativo de M15.

La decision recomendada es usar SSE por `POST` con `text/event-stream` y consumo
frontend via `fetch` streaming. Esto mantiene el body JSON actual para
`message`, `retrieval_limit` y filtros, y evita forzar un `EventSource` nativo
con parametros en URL. FastAPI 0.137.1 en el repo expone `fastapi.sse`, y la
documentacion actual tambien respalda `StreamingResponse` con
`media_type="text/event-stream"` como fallback de implementacion.

## Alcance implementado

- Agregar `POST /projects/{project_id}/chat/stream`.
- Definir eventos SSE estables: `session_started`, `tool_call`, `answer_delta`,
  `heartbeat`, `final` y `error`.
- Hacer que `final` tenga el mismo shape publico que `POST /chat`.
- Conservar `POST /chat` como fallback obligatorio.
- Persistir audit trail final de la misma forma que el flujo no streaming.
- Consumir streaming en frontend con `fetch`, parser SSE y `AbortController`.
- Refrescar historial despues de `final`.
- No guardar deltas parciales como mensajes independientes.

## Fuera de alcance

- WebSockets.
- Dashboard de costo/latencia.
- Replay/re-run, edit, delete o retention de sesiones.
- Auth/autorizacion final.
- Cambios de retrieval, rerank, providers o defaults.
- Persistir cada token delta como mensaje separado.

## Secuencia

1. `m16-chat-streaming-sse`: completo.
2. `m16-streaming-event-contract`: completo.
3. `m16-chat-service-streaming`: completo.
4. `m16-chat-streaming-api`: completo.
5. `m16-chat-streaming-frontend-client`: completo.
6. `m16-chat-streaming-ui`: completo.
7. `m16-quality-gate`: completo.

## Criterio de cierre

M16 quedo cerrado cuando un usuario puede enviar una pregunta desde el frontend,
ver respuesta parcial por streaming, recibir un evento final compatible con
`POST /chat`, refrescar historial desde la sesion persistida, cancelar una
corrida abierta y volver al flujo no streaming cuando el stream no esta
disponible antes de abrirse.
