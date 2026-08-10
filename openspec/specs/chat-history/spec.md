# chat-history Specification

## Purpose
Define la superficie read-only para listar sesiones de chat persistidas y
consultar su detalle auditable por workspace desde API y CLI, reutilizando el
audit trail durable sin re-ejecutar chat, retrieval ni providers.
## Requirements
### Requirement: API lista sesiones de chat por workspace

El sistema MUST exponer una superficie HTTP read-only para listar sesiones de
chat persistidas por workspace, con orden deterministico y limite acotado.

#### Scenario: Listado devuelve sesiones recientes

- **WHEN** `GET /workspaces/{workspace_id}/chat/sessions` se invoca sin filtros
- **THEN** la respuesta contiene sesiones del workspace ordenadas por
  `created_at` descendente y `session_id` como desempate estable
- **AND** cada item incluye `session_id`, `status`, timestamps, metadata de
  modelo/prompt cuando exista y conteos resumidos de mensajes, tool calls,
  retrieval runs y provider usage
- **AND** la respuesta no incluye mensajes completos ni raw provider payloads

#### Scenario: Listado filtra por status

- **WHEN** el cliente envia `status=failed`
- **THEN** la respuesta contiene solo sesiones `failed` del workspace
- **AND** sesiones `running` o `succeeded` no aparecen

#### Scenario: Listado acota resultados

- **WHEN** el cliente envia `limit`
- **THEN** el sistema aplica un maximo estable y rechaza limites invalidos con
  error estable
- **AND** la respuesta incluye cursor o metadata equivalente para pedir la
  pagina siguiente cuando existan mas sesiones

### Requirement: API muestra detalle auditable de una sesion

El sistema MUST exponer una superficie HTTP read-only para consultar el detalle
auditable de una sesion de chat, aislada por workspace.

#### Scenario: Detalle devuelve stepper metadata del assistant

- **WHEN** una sesion contiene un mensaje assistant con `metadata_json.steps`
- **THEN** `GET /workspaces/{workspace_id}/chat/sessions/{session_id}` devuelve el
  campo `metadata.steps` dentro del mensaje correspondiente
- **AND** esos steps preservan `id`, `status`, `elapsed_ms`, `detail` y `usage`
  cuando existan
- **AND** la lectura no re-ejecuta chat, retrieval ni providers

### Requirement: CLI inspecciona historial de chat

El sistema MUST exponer comandos CLI read-only equivalentes a la superficie HTTP
para inspeccionar sesiones persistidas.

#### Scenario: CLI lista sesiones

- **WHEN** `adaptive-rag chat sessions list --workspace-id <uuid>` se ejecuta
- **THEN** el comando escribe JSON estable con los mismos campos resumidos que
  el listado HTTP
- **AND** acepta filtros de status y limite equivalentes

#### Scenario: CLI muestra sesion

- **WHEN** `adaptive-rag chat sessions show --workspace-id <uuid> --session-id <uuid>`
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

### Requirement: Chat history is private to the current user

The system MUST keep chat sessions private per user within a shared workspace.

#### Scenario: User lists only own sessions

- **GIVEN** users `A` and `B` both have access to workspace `P`
- **AND** both users have chat sessions in `P`
- **WHEN** user `A` calls `GET /workspaces/P/chat/sessions`
- **THEN** the response contains only sessions whose owner is user `A`
- **AND** sessions owned by user `B` are not counted or returned

#### Scenario: User cannot inspect another user's session

- **GIVEN** user `B` owns a chat session in workspace `P`
- **AND** user `A` also has access to workspace `P`
- **WHEN** user `A` calls `GET /workspaces/P/chat/sessions/{session_id}` for
  user `B`'s session
- **THEN** the response is not found or an equivalent privacy-preserving error
- **AND** no messages, tool calls, retrieval runs, citations or provider usage
  from user `B` are returned

#### Scenario: Workspace switch resets selected session

- **WHEN** the frontend switches from workspace `A` to workspace `B`
- **THEN** any selected chat session from workspace `A` is cleared
- **AND** history reloads under the current user and workspace `B`

### Requirement: Chat observability respects workspace role

The system MUST restrict workspace chat observability to workspace admins or
superadmins.

#### Scenario: Workspace admin can inspect aggregate observability

- **GIVEN** the current user has workspace role `admin`
- **WHEN** they call workspace chat observability endpoints
- **THEN** aggregate workspace observability is returned
- **AND** private message bodies from other users are not included

#### Scenario: Viewer cannot inspect workspace observability

- **GIVEN** the current user has workspace role `viewer`
- **WHEN** they call workspace chat observability endpoints
- **THEN** the request fails with a stable workspace-role authorization error

### Requirement: Multi-turn history remains consistent on read-back

Continued sessions MUST expose appended turns via the existing session detail
surface in deterministic order.

#### Scenario: History read-back after follow-up

- **WHEN** two chat turns run with the same `session_id`
- **THEN** session detail lists both user messages and both assistant answers
  in creation order

