# chat-tool-calling Specification

## Purpose
Define el contrato conversacional minimo sobre la superficie estable de
retrieval: un servicio compartido que expone retrieval como tool tipada y
adaptadores API/CLI delgados con respuestas citables.
## Requirements
### Requirement: Chat tool calling usa retrieval compartido

El sistema MUST exponer chat mediante un servicio compartido que puede llamar a
una tool de retrieval tipada y MUST reutilizar `RetrievalService` para obtener
contexto. El chat MUST resolver settings efectivos de retrieval por proyecto
antes de ejecutar la tool.

#### Scenario: Chat llama retrieval con settings efectivos

- **WHEN** una solicitud de chat incluye `project_id` y `message`
- **THEN** el servicio conversacional resuelve `retrieval_limit`,
  `rerank_enabled` y `rerank_candidate_limit` desde defaults globales y
  overrides de proyecto
- **AND** la tool llama a `RetrievalService.search()` con `strategy=dense_sparse`
  y filtros tipados
- **AND** si `rerank_enabled=true`, la llamada usa
  `RetrievalRerankOptions(candidate_limit=rerank_candidate_limit)`
- **AND** la tool devuelve resultados serializables con citations

#### Scenario: Request puede acotar retrieval limit de la vuelta

- **WHEN** una solicitud de chat declara `retrieval_limit`
- **THEN** el servicio usa ese limite solo para la vuelta actual
- **AND** valida que el limite este entre `1` y `50`
- **AND** si rerank esta activo, valida que el candidate limit efectivo sea
  mayor o igual al limite final

### Requirement: Chat produce respuestas con citations verificables

El sistema MUST devolver una respuesta estructurada con texto de respuesta,
citations y metadata minima de tool calls, y MUST impedir references a
citations que no fueron devueltas por retrieval.

#### Scenario: Respuesta cita solo resultados recuperados

- **WHEN** la tool de retrieval devuelve citations para chunks recuperados
- **THEN** la respuesta de chat puede incluir esas citations
- **AND** cada citation visible corresponde a un payload devuelto por la tool

#### Scenario: Citation desconocida se rechaza

- **WHEN** el runner/modelo devuelve una respuesta que referencia una citation
  no presente en los resultados de retrieval
- **THEN** el servicio devuelve un error estable
- **AND** no emite una respuesta con evidencia inventada

### Requirement: Chat permite tests deterministas sin red

El sistema MUST permitir ejecutar la capa conversacional con runners y
providers fake, sin llamadas a red ni credenciales live.

#### Scenario: Rerank default usa provider fake/local en tests

- **WHEN** los tests ejecutan una solicitud de chat con settings efectivos
  `rerank_enabled=true`
- **THEN** el servicio puede construir un reranker fake o inyectado
- **AND** reordena candidatos sin llamar providers hosted
- **AND** la respuesta y citations siguen siendo deterministicas

#### Scenario: Rerank disabled no construye provider rerank

- **WHEN** los settings efectivos tienen `rerank_enabled=false`
- **THEN** chat ejecuta retrieval sin `RetrievalRerankOptions`
- **AND** no construye ni valida credenciales de provider rerank

### Requirement: Chat publica API y CLI minimas

El sistema MUST proveer un endpoint FastAPI y un comando Typer que usen el
mismo servicio conversacional.

#### Scenario: API retorna respuesta con citations

- **WHEN** `POST /projects/{project_id}/chat` recibe una solicitud valida
- **THEN** retorna `answer`, `citations` y metadata minima de tool calls
- **AND** usa el mismo servicio conversacional que la CLI

#### Scenario: CLI usa el mismo contrato que API

- **WHEN** `adaptive-rag chat ask` recibe proyecto, pregunta, limite y filtros
- **THEN** llama al mismo servicio conversacional que la API
- **AND** emite una salida JSON estable para tests automatizados

### Requirement: Chat requests execute as the current project user

The system MUST bind every chat request to an authenticated user and project
role before running retrieval or model calls.

#### Scenario: Viewer can start private chat session

- **GIVEN** the current user has project role `viewer`
- **WHEN** they send a chat request for that project
- **THEN** the chat service creates a session owned by that user
- **AND** retrieval uses only approved knowledge from that project
- **AND** the response includes the created session id

#### Scenario: Locked project chat is rejected before providers

- **GIVEN** the current user has no access to a project
- **WHEN** they send a chat request for that project
- **THEN** the request is rejected before retrieval, embeddings or chat
  providers are called

### Requirement: Chat can propose knowledge with auditable origin

The system MUST let users propose new project knowledge from a chat context
without making pending proposals retrievable.

#### Scenario: Viewer proposal remains pending

- **GIVEN** a viewer is chatting in a project
- **WHEN** they propose knowledge from a chat message
- **THEN** the system creates a pending knowledge proposal linked to the
  project, session, message and submitter
- **AND** the proposal does not create chunks or embeddings until approved

#### Scenario: Contributor proposal is approved directly

- **GIVEN** a contributor is chatting in a project
- **WHEN** they propose knowledge from a chat message
- **THEN** the system records an approved proposal or equivalent audit record
- **AND** creates approved source input for ingestion without human review

#### Scenario: Proposal origin is available to reviewers

- **GIVEN** a pending proposal was created from chat
- **WHEN** a contributor opens proposal detail
- **THEN** the response includes enough origin metadata to navigate to the
  source session/message context without exposing unrelated private sessions
