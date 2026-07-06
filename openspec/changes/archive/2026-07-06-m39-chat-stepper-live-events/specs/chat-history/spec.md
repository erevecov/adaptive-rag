# Delta for chat-history

## MODIFIED Requirements

### Requirement: API muestra detalle auditable de una sesion

El sistema MUST exponer una superficie HTTP read-only para consultar el detalle
auditable de una sesion de chat, aislada por proyecto.

#### Scenario: Detalle devuelve stepper metadata del assistant

- **WHEN** una sesion contiene un mensaje assistant con `metadata_json.steps`
- **THEN** `GET /projects/{project_id}/chat/sessions/{session_id}` devuelve el
  campo `metadata.steps` dentro del mensaje correspondiente
- **AND** esos steps preservan `id`, `status`, `elapsed_ms`, `detail` y `usage`
  cuando existan
- **AND** la lectura no re-ejecuta chat, retrieval ni providers
