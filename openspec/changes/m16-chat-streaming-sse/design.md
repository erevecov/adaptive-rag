# Diseno M16 de streaming SSE para chat

## Contexto

M5 cerro `POST /projects/{project_id}/chat` como respuesta JSON completa. M13
agrego audit trail durable para sesiones, mensajes, tool calls, retrieval runs,
citations y provider usage. M14 expuso lectura read-only de historial. M15
agrego un frontend React/TypeScript/Vite que consume `POST /chat` e historial.

La brecha actual es experiencia: el usuario no ve progreso mientras retrieval y
provider chat corren. Streaming debe mejorar ese flujo sin reemplazar el
contrato no streaming, sin mutar historial desde UI y sin introducir dashboards
o replay.

## Decision

La decision recomendada es `proceed` con M16 como streaming SSE por `POST`:

- backend expone `POST /projects/{project_id}/chat/stream`;
- response media type `text/event-stream`;
- FastAPI usa `EventSourceResponse` cuando sea suficiente y conserva
  `StreamingResponse(..., media_type="text/event-stream")` como fallback de
  implementacion si conviene por tests o compatibilidad;
- frontend consume el stream con `fetch` + `ReadableStream`, no con
  `EventSource`, porque el request necesita body JSON;
- el evento final contiene el mismo shape publico que `POST /chat` para que UI,
  historial y tests puedan reconciliar resultado completo.

Esta decision mantiene `POST /chat` como fallback obligatorio y evita forzar
WebSockets antes de tener una necesidad bidireccional real.

## Objetivos

- Agregar contrato de eventos streaming con nombres y payloads estables.
- Preservar `POST /projects/{project_id}/chat` sin cambios incompatibles.
- Emitir `session_started` temprano cuando exista `session_id`.
- Emitir progreso de tool/retrieval y deltas de respuesta cuando el runner lo
  soporte.
- Emitir `final` con `answer`, `citations`, `tool_calls` y `session_id`
  equivalente al response no streaming.
- Emitir `error` estable sin secretos cuando la corrida falle despues de abrir
  el stream.
- Mantener audit trail durable como fuente de verdad para historial.
- Permitir cancelacion desde frontend con `AbortController`.
- Mantener tests deterministas sin red mediante runners/fakes.

## No objetivos

- No reemplazar ni eliminar `POST /projects/{project_id}/chat`.
- No agregar WebSockets.
- No agregar dashboards de costo/latencia.
- No agregar replay/re-run, edit, delete o retention de sesiones.
- No persistir cada token/delta como mensaje independiente del audit trail.
- No cambiar ranking, retrieval, rerank, embeddings ni defaults de providers.
- No convertir historial read-only en superficie mutable.
- No agregar auth/autorizacion final.

## Contrato SSE recomendado

### Endpoint

```text
POST /projects/{project_id}/chat/stream
Accept: text/event-stream
Content-Type: application/json
```

El body debe reutilizar el contrato de `ChatRequestBody` actual:

```json
{
  "message": "Pregunta del usuario",
  "retrieval_limit": 5,
  "metadata_filter": null
}
```

### Eventos

Cada evento debe usar framing SSE estandar con `event:` y `data:`. `data` debe
ser JSON serializable, sin secretos ni raw provider payloads.

Eventos minimos:

- `session_started`: `{ "session_id": "<uuid>" }`
- `tool_call`: `{ "name": "retrieval", "query": "...", "limit": 5, "result_count": 3 }`
- `answer_delta`: `{ "text": "fragmento" }`
- `heartbeat`: `{ "elapsed_ms": 1200 }`
- `final`: mismo shape publico de `ChatResponseBody`
- `error`: `{ "detail": "mensaje estable" }`

Reglas:

- `final` debe emitirse una sola vez en corridas exitosas.
- `error` debe emitirse una sola vez si la corrida falla despues de iniciar el
  stream.
- El stream debe cerrarse despues de `final` o `error`.
- `answer_delta` puede omitirse si el runner live aun no soporta token deltas,
  pero `final` sigue siendo obligatorio para exito.
- `tool_call` puede emitirse cuando la tool termina si no hay evento estable de
  inicio.

## Persistencia y audit trail

- El audit trail debe crear la sesion y mensaje de usuario igual que el flujo no
  streaming.
- La respuesta final del assistant debe persistirse una vez, al completar la
  corrida.
- Tool calls, retrieval runs, citations y provider usage deben persistirse con
  los mismos repositories actuales.
- Si el stream falla despues de crear sesion, la sesion debe quedar `failed`
  con error estable sin secretos.
- Los deltas parciales no se guardan como mensajes separados en M16.
- El historial M14 debe poder leer la sesion final sin conocer el mecanismo de
  streaming.

## Frontend recomendado

- Mantener el flujo no streaming como fallback y como modo de compatibilidad.
- Agregar cliente `askChatStream(projectId, body, handlers, signal)` que:
  - use `fetch` con `POST`;
  - valide status HTTP antes de procesar chunks;
  - parse eventos SSE aunque lleguen partidos por chunks;
  - acumule `answer_delta`;
  - reemplace el estado final con el payload `final`;
  - soporte `AbortController`;
  - convierta errores de red/HTTP/SSE en mensajes legibles.
- UI:
  - mostrar estado streaming y boton de cancelacion;
  - mostrar respuesta parcial mientras llegan deltas;
  - mostrar tool calls/progreso cuando existan;
  - refrescar historial despues del `final`;
  - volver a `POST /chat` si streaming no esta disponible o se deshabilita.

## Secuencia recomendada de M16

### 1. `m16-chat-streaming-sse`

Alcance:

- Crear el change OpenSpec M16.
- Documentar contrato SSE, persistencia, frontend y slices.
- Actualizar progress/roadmap y arquitectura.

Fuera de alcance:

- Codigo productivo backend/frontend.

### 2. `m16-streaming-event-contract`

Alcance:

- Agregar modelos/tipos internos para eventos streaming.
- Definir serializer SSE determinista con tests unitarios.
- Mantener `ChatResponseBody` como shape de `final`.

Fuera de alcance:

- Endpoint HTTP.

### 3. `m16-chat-service-streaming`

Alcance:

- Agregar metodo streaming o wrapper alrededor de `ChatService` que comparta
  validacion, audit trail, citations y provider usage.
- Agregar runner/fake determinista capaz de emitir deltas.
- Mantener `respond()` sin cambios incompatibles.

Fuera de alcance:

- Frontend.

### 4. `m16-chat-streaming-api`

Alcance:

- Agregar `POST /projects/{project_id}/chat/stream`.
- Usar `EventSourceResponse` o `StreamingResponse` con `text/event-stream`.
- Cubrir success, error, invalid request y stream close en tests.

Fuera de alcance:

- WebSockets.

### 5. `m16-chat-streaming-frontend-client`

Alcance:

- Agregar parser SSE y cliente `fetch` streaming.
- Cubrir chunks partidos, multiples eventos por chunk, errores y cancelacion.

Fuera de alcance:

- Cambios visuales completos.

### 6. `m16-chat-streaming-ui`

Alcance:

- Integrar streaming en la pantalla de chat.
- Mostrar deltas, progreso, cancelacion y fallback no streaming.
- Refrescar historial al recibir `final`.

Fuera de alcance:

- Dashboard, replay, edit/delete de sesiones.

### 7. `m16-quality-gate`

Alcance:

- Validar frontend, Python y OpenSpec.
- Ejecutar QA local de streaming cuando exista implementacion.
- Archivar el change M16 al completar el milestone.

## Riesgos y mitigaciones

- Riesgo: confundir SSE con EventSource nativo y perder body JSON.
  Mitigacion: contrato usa `POST` + `fetch` streaming.
- Riesgo: duplicar logica de chat entre streaming y no streaming.
  Mitigacion: compartir validacion, audit writer, retrieval tool y final
  serializer.
- Riesgo: persistir deltas parciales como mensajes incoherentes.
  Mitigacion: M16 solo persiste mensaje final del assistant.
- Riesgo: provider live no soporte deltas inmediatamente.
  Mitigacion: `final` es obligatorio; `answer_delta` se emite solo cuando el
  runner lo soporte, y el frontend mantiene fallback.
- Riesgo: streams colgados durante tool calls largas.
  Mitigacion: heartbeat acotado y cancelacion via `AbortController`.

## Validacion esperada por slice

Planificacion:

```text
pnpm dlx @fission-ai/openspec validate m16-chat-streaming-sse --strict
pnpm dlx @fission-ai/openspec validate --specs --strict
pnpm dlx @fission-ai/openspec list
git diff --check
```

Implementacion posterior:

```text
uv run pytest
uv run ruff check .
uv run mypy src
cd frontend && pnpm test
cd frontend && pnpm run lint
cd frontend && pnpm run typecheck
cd frontend && pnpm run build
```
