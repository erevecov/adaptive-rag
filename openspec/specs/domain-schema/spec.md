# domain-schema Specification

## Purpose

Definir el schema persistente multi-project de Adaptive RAG para proyectos,
fuentes, documentos, versiones normalizadas, chunks y sparse embeddings,
incluyendo aislamiento por `project_id`, metadata filtering y compatibilidad
con pgvector/Qwen.
## Requirements
### Requirement: Registros de proyecto definen aislamiento y modo de retrieval

El sistema MUST persistir registros de proyecto que aislen todos los datos RAG por `project_id` y definan configuracion de retrieval.

#### Scenario: Proyecto usa dense_sparse retrieval por defecto

- **WHEN** se crea un proyecto sin modo de embedding explicito
- **THEN** el `embedding_mode` guardado es `dense_sparse`
- **AND** `retrieval_contextualization_enabled` es `true`

#### Scenario: Configuracion de presupuesto del proyecto queda persistida

- **WHEN** un proyecto incluye configuracion de presupuesto
- **THEN** esa configuracion se guarda en `budget_config_json`

### Requirement: Sources y documents preservan identidad de ingestion

El sistema MUST persistir sources y documents con identificadores estables, source type, identificadores externos, metadata y pertenencia a proyecto.

#### Scenario: Documents pertenecen a un proyecto y source

- **WHEN** se crea un document desde un source
- **THEN** el document guarda `project_id` y `source_id`
- **AND** las queries de repository pueden filtrar por cualquiera de esos campos

#### Scenario: Metadata de source soporta filtering

- **WHEN** un source tiene tags, source type o metadata de fecha
- **THEN** esos valores se guardan en columnas tipadas o campos de metadata indexados aptos para filtering

### Requirement: Document versions anclan texto normalizado y citas

El sistema MUST guardar cada document version parseada con texto normalizado, parser metadata, extraction metadata, content hash e index fingerprint.

#### Scenario: Offsets de chunk refieren a texto normalizado

- **WHEN** se crea un chunk para una document version
- **THEN** `char_start` y `char_end` refieren a offsets en `document_versions.normalized_text`

#### Scenario: Re-indexing preserva document versions anteriores

- **WHEN** un document se re-parsea con texto normalizado o parser metadata distinta
- **THEN** se crea una fila nueva en `document_versions`
- **AND** los chunks existentes siguen apuntando a su version original

### Requirement: Chunks guardan inputs de embedding denso y limites semanticos

El sistema MUST persistir chunks con section metadata, conteo de tokens, enlaces vecinos, chunker metadata, campos reservados para contextual retrieval y embeddings densos.

#### Scenario: Columna de embedding denso tiene dimensiones compatibles con Qwen

- **WHEN** se migra el schema
- **THEN** `chunks.embedding` es una columna pgvector con 1024 dimensiones

#### Scenario: Lineage de chunks se puede reconstruir

- **WHEN** se recuperan chunks de una document version
- **THEN** `ordinal`, `prev_chunk_id` y `next_chunk_id` permiten reconstruir el orden local de chunks

### Requirement: Sparse embeddings son opcionales y aislados

El sistema MUST guardar datos de sparse embeddings en `chunk_sparse_embeddings` solo cuando un proyecto usa modo `dense_sparse`.

#### Scenario: Proyectos dense-only no necesitan filas sparse

- **WHEN** un proyecto usa `embedding_mode = dense`
- **THEN** retrieval puede operar sin filas en `chunk_sparse_embeddings`

#### Scenario: Filas sparse preservan metadata de reproducibilidad

- **WHEN** se guardan sparse embeddings
- **THEN** cada fila incluye sparse indices, sparse values, sparse tokens opcionales, sparse size, input hash e index fingerprint

### Requirement: Current project and source schema supports public authoring

The existing project and source tables MUST be sufficient for M23 public
authoring unless implementation evidence proves a required product field is
missing.

#### Scenario: Project authoring uses existing project fields

- **WHEN** a project is created through the M23 public surface
- **THEN** it uses existing project fields such as `name`, `embedding_mode`,
  `retrieval_contextualization_enabled` and `budget_config_json`
- **AND** it does not require a migration for auth multi-user, slug or hosted
  settings

#### Scenario: Source authoring uses existing source fields

- **WHEN** a source is created through the M23 public surface
- **THEN** it uses existing source fields such as `project_id`, `source_type`,
  `external_id`, `tags` and `extra_metadata`
- **AND** inline text content for text-like sources is stored in
  `extra_metadata.content` for the current ingestion pipeline

### Requirement: Domain schema supports local users and project memberships

The system MUST persist local users and project memberships so project access
can be authorized without relying on external auth providers.

#### Scenario: User records carry system role and active state

- **WHEN** a user is created
- **THEN** the row stores a stable id, unique login identifier, display name,
  `system_role`, `is_active`, `created_at` and `updated_at`
- **AND** `system_role` is constrained to `superadmin` or `user`

#### Scenario: Project membership records carry project role

- **WHEN** a user is assigned to a project
- **THEN** the membership stores `project_id`, `user_id`, role and timestamps
- **AND** role is constrained to `admin`, `contributor` or `viewer`
- **AND** active duplicate memberships for the same user/project are rejected

### Requirement: Chat sessions belong to a user

The system MUST persist the owner user on every chat session.

#### Scenario: New chat session stores user id

- **WHEN** an authenticated user starts a chat in a project
- **THEN** the new `chat_sessions` row stores both `project_id` and `user_id`
- **AND** downstream messages, tool calls and retrieval runs remain linked to
  that session

#### Scenario: Existing session indexes support user-scoped listing

- **WHEN** chat sessions are listed for a project and user
- **THEN** the schema supports efficient filtering by `project_id`, `user_id`
  and `created_at`

### Requirement: Knowledge proposals preserve chat origin before ingestion

The system MUST persist chat-sourced knowledge proposals separately from
approved sources/documents/chunks.

#### Scenario: Viewer proposal starts pending

- **WHEN** a viewer proposes knowledge from chat
- **THEN** a `knowledge_proposals` row is created with `status = "pending"`
- **AND** it stores project, submitter, proposed text and chat origin

#### Scenario: Approved proposal records reviewer and source

- **WHEN** a contributor or admin approves a proposal
- **THEN** the proposal stores `status = "approved"`, reviewer, reviewed time
  and the source id created for ingestion

#### Scenario: Rejected proposal records reason

- **WHEN** a contributor or admin rejects a proposal
- **THEN** the proposal stores `status = "rejected"`, reviewer, reviewed time
  and a non-empty rejection reason

