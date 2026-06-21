# chat-history Specification

## Purpose
Define la superficie read-only para listar sesiones de chat persistidas y
consultar su detalle auditable por proyecto desde API y CLI, reutilizando el
audit trail durable sin re-ejecutar chat, retrieval ni providers.

## Requirements
### Requirement: API lista sesiones de chat por proyecto

El sistema MUST exponer una superficie HTTP read-only para listar sesiones de
chat persistidas por proyecto, con orden deterministico y limite acotado.

#### Scenario: Listado devuelve sesiones recientes

- **WHEN** `GET /projects/{project_id}/chat/sessions` se invoca sin filtros
- **THEN** la respuesta contiene sesiones del proyecto ordenadas por
  `created_at` descendente y `session_id` como desempate estable
- **AND** cada item incluye `session_id`, `status`, timestamps, metadata de
  modelo/prompt cuando exista y conteos resumidos de mensajes, tool calls,
  retrieval runs y provider usage
- **AND** la respuesta no incluye mensajes completos ni raw provider payloads

#### Scenario: Listado filtra por status

- **WHEN** el cliente envia `status=failed`
- **THEN** la respuesta contiene solo sesiones `failed` del proyecto
- **AND** sesiones `running` o `succeeded` no aparecen

#### Scenario: Listado acota resultados

- **WHEN** el cliente envia `limit`
- **THEN** el sistema aplica un maximo estable y rechaza limites invalidos con
  error estable
- **AND** la respuesta incluye cursor o metadata equivalente para pedir la
  pagina siguiente cuando existan mas sesiones

### Requirement: API muestra detalle auditable de una sesion

El sistema MUST exponer una superficie HTTP read-only para consultar el detalle
auditable de una sesion de chat, aislada por proyecto.

#### Scenario: Detalle devuelve audit trail completo

- **WHEN** `GET /projects/{project_id}/chat/sessions/{session_id}` se invoca
  para una sesion del proyecto
- **THEN** la respuesta incluye metadata de sesion, mensajes, tool calls,
  retrieval runs, retrieved chunks/citations y provider usage
- **AND** mensajes, tool calls, retrieval runs y provider usage se ordenan por
  `created_at` ascendente
- **AND** retrieved chunks se ordenan por `rank` dentro de cada retrieval run

#### Scenario: Detalle conserva citations persistidas

- **WHEN** una sesion contiene retrieved chunks con `citation_json`
- **THEN** la respuesta de detalle devuelve esas citations persistidas sin
  recalcular retrieval ni tocar embeddings/providers

#### Scenario: Detalle no filtra datos cross-project

- **WHEN** un cliente pide un `session_id` que pertenece a otro proyecto
- **THEN** el sistema responde con no encontrado o error estable equivalente
- **AND** no revela datos de la sesion de otro proyecto

### Requirement: CLI inspecciona historial de chat

El sistema MUST exponer comandos CLI read-only equivalentes a la superficie HTTP
para inspeccionar sesiones persistidas.

#### Scenario: CLI lista sesiones

- **WHEN** `adaptive-rag chat sessions list --project-id <uuid>` se ejecuta
- **THEN** el comando escribe JSON estable con los mismos campos resumidos que
  el listado HTTP
- **AND** acepta filtros de status y limite equivalentes

#### Scenario: CLI muestra sesion

- **WHEN** `adaptive-rag chat sessions show --project-id <uuid> --session-id <uuid>`
  se ejecuta
- **THEN** el comando escribe JSON estable con el detalle auditable de la sesion
- **AND** no re-ejecuta chat, retrieval ni providers

### Requirement: M14 preserva alcance read-only

El sistema MUST mantener M14 como una superficie de lectura y no introducir
streaming, dashboard, replay ni cambios de ranking.

#### Scenario: Lectura no muta audit trail

- **WHEN** API o CLI consultan listados o detalle de sesiones
- **THEN** no crean mensajes, tool calls, retrieval runs ni provider usage
- **AND** no cambian el status de sesiones existentes

#### Scenario: No hay replay ni streaming

- **WHEN** M14 queda implementado
- **THEN** no agrega endpoints SSE/WebSocket
- **AND** no agrega comandos para re-ejecutar o modificar sesiones
- **AND** no cambia `RetrievalService`, rerank, providers ni defaults de
  retrieval
