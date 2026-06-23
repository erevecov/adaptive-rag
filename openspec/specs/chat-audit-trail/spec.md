# chat-audit-trail Specification

## Purpose
Define la persistencia durable del audit trail de chat: sesiones, mensajes,
tool calls, retrieval runs, retrieved chunks, citations y usage/cost asociados,
manteniendo aislamiento por proyecto y sin convertir M13 en streaming,
historial publico ni dashboards.
## Requirements
### Requirement: Chat persiste audit trail durable

El sistema MUST persistir un audit trail durable para cada corrida valida de
chat, incluyendo sesion, mensajes, tool calls, retrieval runs, retrieved chunks
y citations.

#### Scenario: Chat exitoso guarda sesion y mensajes

- **WHEN** una solicitud valida de chat produce una respuesta final
- **THEN** el sistema guarda una sesion de chat con `project_id`, status
  `succeeded`, timestamps y metadata de modelo/prompt cuando exista
- **AND** guarda el mensaje del usuario y el mensaje final del assistant
- **AND** la respuesta publica puede incluir un identificador de sesion estable
  para trazabilidad

#### Scenario: Tool call queda auditada

- **WHEN** el runner solicita una tool de retrieval durante una sesion
- **THEN** el sistema guarda una tool call con nombre, argumentos serializables,
  status, latencia y resumen de resultado
- **AND** no guarda secretos, API keys ni credenciales en argumentos o metadata

#### Scenario: Retrieval run de chat conserva citations

- **WHEN** una tool de retrieval devuelve chunks citables para una sesion
- **THEN** el sistema guarda un retrieval run asociado a la sesion o tool call
- **AND** guarda cada chunk recuperado con `chunk_id`, rank, scores disponibles
  y `citation_json`
- **AND** cada citation persistida corresponde a un resultado devuelto por
  `RetrievalService`

#### Scenario: Fallo de chat queda auditable

- **WHEN** una corrida de chat falla despues de crear la sesion
- **THEN** el sistema marca la sesion o evento relevante como `failed`
- **AND** guarda un `error_message` estable sin secretos
- **AND** preserva los mensajes, tool calls o retrieval runs completados antes
  del fallo

### Requirement: Audit trail conserva aislamiento por proyecto

El sistema MUST aislar todos los registros de audit trail por `project_id` y
MUST impedir que repositories lean o escriban datos de otro proyecto.

#### Scenario: Repository filtra por proyecto

- **WHEN** se consultan sesiones, mensajes, tool calls o retrieval runs mediante
  repository
- **THEN** la query aplica `project_id` cuando el registro o su padre pertenece
  a un proyecto
- **AND** una consulta para otro proyecto no devuelve datos cruzados

#### Scenario: Retrieved chunks apuntan a chunks existentes

- **WHEN** se persiste un chunk recuperado en el audit trail
- **THEN** el registro referencia un chunk del mismo proyecto que la sesion
- **AND** la operacion falla con error estable si el chunk pertenece a otro
  proyecto

### Requirement: Provider usage se vincula a contexto durable

El sistema MUST poder vincular metadata de usage/cost de providers a un contexto
durable de proyecto, sesion, job o eval run sin romper los runners offline.

#### Scenario: Usage de chat se asocia a sesion

- **WHEN** una llamada live de chat, embedding o rerank ocurre dentro de una
  sesion de chat
- **THEN** el usage record guarda `project_id`, `session_id`, provider, modelo,
  operation, tokens/unidades disponibles, costo estimado, status y latencia
- **AND** los campos ausentes del provider se representan como ausentes, no
  inventados

#### Scenario: Evals y jobs pueden registrar usage sin sesion

- **WHEN** un eval o job registra usage fuera de una sesion de chat
- **THEN** el usage record puede guardar `eval_run_id` o `job_id` sin
  `session_id`
- **AND** conserva `project_id`, provider, modelo, operation, status y costo
  estimado cuando exista

#### Scenario: Offline sigue sin red ni credenciales

- **WHEN** tests, API/CLI local o evals offline usan providers fake
- **THEN** el audit trail puede registrar metadata fake determinista
- **AND** no requiere credenciales live ni llamadas de red hosted

### Requirement: API y CLI preservan contratos principales

El sistema MUST integrar audit trail en API y CLI sin convertir M13 en historial
de sesiones ni streaming.

#### Scenario: Endpoint de chat mantiene respuesta compatible

- **WHEN** `POST /projects/{project_id}/chat` recibe una solicitud valida
- **THEN** retorna `answer`, `citations` y metadata minima de tool calls como
  antes
- **AND** puede incluir `session_id` como metadata de trazabilidad
- **AND** no requiere que el cliente gestione transacciones de audit trail

#### Scenario: CLI de chat persiste la misma corrida

- **WHEN** `adaptive-rag chat ask` recibe una pregunta valida
- **THEN** llama al mismo servicio conversacional que la API
- **AND** persiste el mismo tipo de audit trail
- **AND** no agrega comandos de historial en M13

### Requirement: Audit trail stores lexical and RRF scores when present

The chat audit trail MUST preserve retrieval score metadata for non-dense
strategies without changing the default chat retrieval strategy.

#### Scenario: Retrieved chunks store strategy scores

- **WHEN** serialized retrieval results include dense, lexical or RRF score
  metadata
- **THEN** durable retrieved chunk rows store those values in the existing score
  columns
- **AND** missing score metadata remains nullable for legacy dense results
