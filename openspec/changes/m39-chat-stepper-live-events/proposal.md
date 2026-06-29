# Propuesta M39 de chat stepper live events

## Contexto

El chat ya expone streaming SSE, historial durable y un inspector read-only de
tool calls, retrieval runs y provider usage. La UI no muestra todavia el avance
interno de una respuesta junto al turno actual ni rehidrata ese avance desde el
mensaje persistido del assistant.

El usuario valido un diseno estilo BeFlow para un stepper local a la respuesta:
expandible durante streaming, colapsable con preferencia persistida y con
detalle de modelo, tokens, costo, latencia, sources y errores cuando existan.

## Objetivo

Agregar un contrato backend/frontend de stepper para chat que:

- emita eventos SSE `step` durante la corrida;
- persista el snapshot final en `ChatHistoryMessage.metadata.steps`;
- renderice el mismo stepper durante streaming y al leer historial;
- preserve la preferencia expandido/colapsado en `localStorage`.

## Alcance

Incluye:

- Tipos y serializacion de eventos `step` de chat.
- Wiring de `ChatService.stream` y `ChatRetrievalTool` para steps de
  `answer` y `retrieval`.
- Persistencia de steps terminales en el mensaje assistant.
- Parser frontend de `step`, helpers de metadata y preferencia.
- Renderer React para estado streaming y respuesta final.
- Tests backend, frontend y OpenSpec strict.

No incluye:

- Cambiar retrieval, rerank o ranking defaults.
- Nuevos endpoints, WebSocket, replay o edicion de sesiones.
- Costos perfectos cuando no hay provider usage.
- Substeps con timings inventados si el backend no los mide.
