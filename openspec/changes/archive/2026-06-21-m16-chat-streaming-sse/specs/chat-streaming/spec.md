# Delta for chat-streaming

## ADDED Requirements

### Requirement: Chat expone streaming SSE por POST

El sistema MUST exponer una superficie HTTP streaming para chat que preserve el
body JSON del contrato actual y devuelva eventos `text/event-stream`.

#### Scenario: Endpoint acepta request de chat por POST

- **WHEN** el cliente envia una solicitud valida a
  `POST /projects/{project_id}/chat/stream`
- **THEN** el sistema procesa `message`, `retrieval_limit` y `metadata_filter`
  con las mismas reglas del flujo no streaming
- **AND** responde con media type `text/event-stream`
- **AND** no requiere mover el mensaje ni filtros a query params

#### Scenario: Flujo no streaming sigue disponible

- **WHEN** M16 queda implementado
- **THEN** `POST /projects/{project_id}/chat` sigue retornando el JSON final
  compatible
- **AND** clientes que no soportan streaming pueden usar el endpoint existente

### Requirement: SSE usa eventos versionados y final compatible

El sistema MUST emitir eventos SSE con nombres y payloads estables, y MUST
cerrar cada stream exitoso con un evento final compatible con la respuesta de
chat existente.

#### Scenario: Stream exitoso emite progreso y final

- **WHEN** una corrida streaming completa exitosamente
- **THEN** el stream puede emitir `session_started`, `tool_call`,
  `answer_delta` y `heartbeat`
- **AND** emite exactamente un evento `final`
- **AND** el payload `final` contiene `answer`, `citations`, `tool_calls` y
  `session_id` con el mismo shape publico de `POST /chat`
- **AND** el stream se cierra despues de `final`

#### Scenario: Stream fallido emite error estable

- **WHEN** una corrida streaming falla despues de iniciar el stream
- **THEN** el sistema emite exactamente un evento `error` con `detail` estable
  sin secretos
- **AND** no emite `final`
- **AND** el stream se cierra despues de `error`

### Requirement: Streaming conserva audit trail e historial

El sistema MUST persistir sesiones streaming usando el mismo audit trail durable
que el flujo no streaming, sin guardar deltas parciales como mensajes
independientes.

#### Scenario: Corrida streaming exitosa queda auditable

- **WHEN** una corrida streaming termina con `final`
- **THEN** el audit trail guarda sesion, mensaje de usuario, mensaje final del
  assistant, tool calls, retrieval runs, citations y provider usage disponibles
- **AND** el historial read-only puede consultar la sesion sin conocer el
  mecanismo de streaming

#### Scenario: Corrida streaming fallida queda marcada failed

- **WHEN** una corrida streaming falla despues de crear sesion
- **THEN** la sesion queda marcada `failed` con error estable sin secretos
- **AND** se preservan los mensajes, tool calls, retrieval runs o usage ya
  completados antes del fallo

### Requirement: Frontend consume streaming con fallback

El sistema MUST permitir que el frontend consuma SSE por `fetch` streaming,
muestre progreso y conserve fallback al flujo no streaming.

#### Scenario: Cliente frontend procesa chunks SSE

- **WHEN** el backend emite eventos SSE que llegan partidos o agrupados en
  chunks HTTP
- **THEN** el cliente frontend reconstruye eventos completos
- **AND** acumula `answer_delta` para mostrar respuesta parcial
- **AND** reemplaza el estado final con el payload `final`

#### Scenario: Usuario cancela streaming

- **WHEN** el usuario cancela una corrida en progreso desde la UI
- **THEN** el frontend aborta el request con `AbortController`
- **AND** la UI queda en estado cancelado o idle sin mostrar una respuesta final
  inventada
- **AND** el usuario puede enviar una nueva pregunta despues de cancelar

#### Scenario: Frontend cae al flujo no streaming

- **WHEN** streaming no esta disponible, falla antes de abrir el stream o se
  deshabilita por configuracion local
- **THEN** el frontend puede usar `POST /projects/{project_id}/chat`
- **AND** mantiene loading, error, citations, tool calls e historial como en
  M15

### Requirement: M16 no amplia alcance fuera de streaming

El sistema MUST mantener M16 enfocado en streaming de chat y no introducir
superficies de producto independientes.

#### Scenario: No hay WebSockets ni dashboards

- **WHEN** M16 queda implementado
- **THEN** no agrega WebSockets
- **AND** no agrega dashboards de costo/latencia
- **AND** no agrega replay, edit, delete ni retention de sesiones
- **AND** no cambia retrieval, rerank, providers ni defaults de ranking
