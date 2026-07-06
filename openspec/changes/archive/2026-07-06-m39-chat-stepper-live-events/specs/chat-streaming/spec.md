# Delta for chat-streaming

## MODIFIED Requirements

### Requirement: SSE usa eventos versionados y final compatible

El sistema MUST emitir eventos SSE con nombres y payloads estables, y MUST
cerrar cada stream exitoso con un evento final compatible con la respuesta de
chat existente.

#### Scenario: Stream exitoso emite progreso, steps y final

- **WHEN** una corrida streaming completa exitosamente
- **THEN** el stream puede emitir `session_started`, `tool_call`,
  `answer_delta`, `heartbeat` y `step`
- **AND** cada evento `step` contiene `id`, `status`, y opcionalmente
  `elapsed_ms`, `detail` y `usage`
- **AND** emite exactamente un evento `final`
- **AND** el payload `final` contiene `answer`, `citations`, `tool_calls` y
  `session_id` con el mismo shape publico de `POST /chat`
- **AND** el stream se cierra despues de `final`

#### Scenario: Stream fallido emite step de error cuando hay fase activa

- **WHEN** una corrida streaming falla despues de iniciar una fase medida
- **THEN** el sistema emite un evento `step` con `status=error` cuando puede
  asociar el fallo a una fase estable
- **AND** emite exactamente un evento `error` con `detail` estable sin secretos
- **AND** no emite `final`
- **AND** el stream se cierra despues de `error`

### Requirement: Streaming conserva audit trail e historial

El sistema MUST persistir sesiones streaming usando el mismo audit trail durable
que el flujo no streaming, sin guardar deltas parciales como mensajes
independientes.

#### Scenario: Corrida streaming exitosa persiste steps del assistant

- **WHEN** una corrida streaming termina con `final`
- **THEN** el audit trail guarda el mensaje final del assistant con
  `metadata.steps`
- **AND** cada step persistido usa un estado terminal `done` o `error`
- **AND** el historial read-only puede consultar esos steps sin re-ejecutar
  chat, retrieval ni providers

### Requirement: Frontend consume streaming con fallback

El sistema MUST permitir que el frontend consuma SSE por `fetch` streaming,
muestre progreso y conserve fallback al flujo no streaming.

#### Scenario: Cliente frontend procesa eventos step

- **WHEN** el backend emite eventos `step` partidos o agrupados en chunks HTTP
- **THEN** el cliente frontend reconstruye los eventos completos
- **AND** invoca el handler de steps con `id`, `status`, `elapsed_ms`, `detail`
  y `usage` tipados
- **AND** sigue acumulando `answer_delta` y reemplaza el estado final con el
  payload `final`
