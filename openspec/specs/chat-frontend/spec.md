# chat-frontend Specification

## Purpose
Define la primera superficie frontend de Adaptive RAG para chat e historial
read-only sobre los contratos backend existentes, manteniendo el cliente
aislado bajo `frontend/` y sin ampliar el alcance de retrieval, providers,
streaming, replay o dashboards.
## Requirements
### Requirement: Frontend inicial usa scaffold dedicado

El sistema MUST agregar un frontend dedicado para la primera UI de chat sin
mezclar dependencias Node con el paquete Python principal.

#### Scenario: Scaffold queda aislado

- **WHEN** se implemente el scaffold frontend de M15
- **THEN** los archivos de app, build tooling y lockfile Node quedan bajo un
  directorio dedicado como `frontend/`
- **AND** el paquete Python existente sigue instalable y testeable sin instalar
  dependencias Node

#### Scenario: Stack usa React TypeScript con Vite

- **WHEN** se cree el frontend inicial
- **THEN** usa React, TypeScript y Vite con plugin React oficial o equivalente
  vigente al momento de implementacion
- **AND** expone scripts documentados para dev, build, lint y test

### Requirement: Frontend consume contratos API existentes

El sistema MUST consumir los contratos HTTP ya cerrados para chat e historial,
sin consultar tablas internas ni duplicar logica backend.

#### Scenario: Cliente envia pregunta de chat

- **WHEN** el usuario envia una pregunta desde la UI con `project_id`
- **THEN** el frontend llama `POST /projects/{project_id}/chat`
- **AND** muestra `answer`, `citations`, `tool_calls` y `session_id` cuando
  existan en la respuesta

#### Scenario: Cliente lista sesiones persistidas

- **WHEN** el usuario abre o refresca el historial de un proyecto
- **THEN** el frontend llama `GET /projects/{project_id}/chat/sessions`
- **AND** renderiza sesiones ordenadas segun el contrato backend
- **AND** soporta limite/cursor solo mediante parametros publicos del endpoint

#### Scenario: Cliente muestra detalle read-only

- **WHEN** el usuario selecciona una sesion persistida
- **THEN** el frontend llama
  `GET /projects/{project_id}/chat/sessions/{session_id}`
- **AND** muestra mensajes, tool calls, retrieval runs, citations y provider
  usage disponibles
- **AND** no re-ejecuta chat, retrieval ni providers

### Requirement: UI base es operativa y no marketing

El sistema MUST presentar una experiencia de trabajo directa para chat e
historial como primera pantalla del frontend.

#### Scenario: Primera pantalla permite trabajar

- **WHEN** el usuario abre la app frontend
- **THEN** ve controles para elegir o ingresar `project_id`, enviar una pregunta
  y revisar sesiones recientes
- **AND** no se muestra una landing page como pantalla principal

#### Scenario: Estados basicos quedan cubiertos

- **WHEN** la UI espera una respuesta, no tiene datos o recibe error HTTP/red
- **THEN** muestra estados de loading, empty y error claros
- **AND** preserva el input del usuario cuando una solicitud falla

### Requirement: Frontend no expone secretos ni cambia alcance backend

El sistema MUST mantener el frontend como cliente de API sin secretos y sin
alterar contratos backend fuera del alcance M15.

#### Scenario: Configuracion publica no contiene credenciales

- **WHEN** se configure la base URL del backend para dev/build
- **THEN** se usa una variable publica de frontend como
  `VITE_ADAPTIVE_RAG_API_BASE_URL` o equivalente
- **AND** no se requiere ni documenta provider API key en el browser

#### Scenario: M15 no agrega streaming ni replay

- **WHEN** M15 quede implementado
- **THEN** no agrega endpoints SSE/WebSocket
- **AND** no agrega replay, delete, edit, retention ni dashboards
- **AND** no cambia retrieval, rerank, providers ni defaults de ranking

### Requirement: Frontend exposes a read-only chat observability dashboard

The frontend MUST expose a read-only dashboard for chat observability using the
public API contracts already exposed by the backend.

#### Scenario: User filters observability by project and time range

- **WHEN** the user enters a `project_id`, optional `created_at_from`,
  `created_at_to` and `status` filters, then refreshes observability
- **THEN** the frontend calls
  `GET /projects/{project_id}/chat/observability/summary`
- **AND** sends only non-empty public query parameters
- **AND** preserves the filter inputs when the request fails

#### Scenario: Dashboard renders summary cards and breakdowns

- **WHEN** a summary response is loaded
- **THEN** the frontend renders session total, provider usage total, estimated
  known cost, error counts and status breakdowns
- **AND** renders provider usage groups by operation, provider and model
- **AND** labels latency values according to the backend aggregate actually
  used

#### Scenario: Dashboard renders recent session health read-only

- **WHEN** the dashboard needs a recent session health table
- **THEN** the frontend may call `GET /projects/{project_id}/chat/sessions`
  with public list parameters
- **AND** displays only session summary fields such as status, counts,
  timestamps and estimated cost
- **AND** does not replay, edit, delete or re-run chat sessions

#### Scenario: Dashboard handles operational states

- **WHEN** observability data is loading, empty or fails with HTTP/network
  errors
- **THEN** the frontend shows clear loading, empty and error states
- **AND** does not clear valid user filters on failure
- **AND** does not require provider API keys or secrets in the browser

#### Scenario: Dashboard does not expand backend scope

- **WHEN** the frontend observability dashboard is implemented
- **THEN** it remains a client of public API contracts
- **AND** it does not query internal tables directly
- **AND** it does not change retrieval, rerank, provider, streaming or graph
  defaults

### Requirement: Frontend exposes compact project and source authoring

The frontend MUST expose a compact working surface for creating or selecting a
project and adding sources before chat, without becoming a marketing page or
changing backend contracts outside M23.

#### Scenario: User creates or selects a project

- **WHEN** the user opens the frontend without a known `project_id`
- **THEN** the UI provides controls to create a project or choose an existing
  project from the public API
- **AND** the selected project id is used by chat, history and observability
  requests
- **AND** valid user inputs are preserved when project requests fail

#### Scenario: User adds and reviews sources

- **WHEN** a project is selected
- **THEN** the UI provides controls to add supported sources and list existing
  sources for that project
- **AND** source creation does not claim that ingestion or indexing has already
  run
- **AND** valid user inputs are preserved when source requests fail

### Requirement: Frontend exposes ingestion job operations

The frontend MUST expose compact ingestion controls alongside project/source
authoring.

#### Scenario: User enqueues and reviews ingestion jobs

- **WHEN** a project has sources in the authoring view
- **THEN** the UI provides a control to enqueue ingestion for a source
- **AND** the UI can list jobs for the selected project
- **AND** each listed job shows status and last error when present

#### Scenario: User runs or retries ingestion locally

- **WHEN** the user runs the next ingestion job from the UI
- **THEN** the UI shows whether the operation processed, blocked or found no job
- **AND** retry controls are only offered for `blocked` or `dead_letter` jobs

### Requirement: Frontend onboarding points to seeded chat data

The frontend documentation MUST help users create cited local data before using
the chat workspace.

#### Scenario: User prepares data before opening chat UI

- **WHEN** a user follows the first-run runbook
- **THEN** the docs explain how to create a project with cited data using
  `adaptive-rag first-run smoke`
- **AND** the resulting project id can be reused in the chat UI

### Requirement: Frontend exposes Runtime settings without secrets

The frontend MUST expose global runtime/provider configuration and project
runtime overrides through public backend contracts without storing or rendering
provider secrets in the browser.

#### Scenario: User manages global provider connections

- **WHEN** a user opens Runtime settings
- **THEN** the UI can list configured provider connections, readiness status
  and supported slot capabilities
- **AND** hosted and local connections can both be visible at the same time
- **AND** no plaintext API key, ciphertext or Authorization header is rendered
- **AND** creating a connection does not ask the user to type an internal
  connection ID

#### Scenario: User saves or rotates a provider secret

- **WHEN** a user enters a provider secret in the Runtime settings UI
- **THEN** the frontend sends it only to the backend save/rotate endpoint
- **AND** clears the input after success or failure
- **AND** subsequent reads show only safe status such as configured time or
  non-reversible fingerprint
- **AND** the connection target is selected from existing connections

#### Scenario: User configures fixed global slots

- **WHEN** a user edits global runtime defaults
- **THEN** the UI presents only the fixed slots `chat`, `dense_embedding`,
  `sparse_embedding`, `rerank` and `contextualization`
- **AND** slot controls only offer compatible connections/models
- **AND** model controls are selectors populated from the persisted provider
  model catalog and current saved settings

#### Scenario: Chat pool exposes one default

- **WHEN** the global chat model pool has multiple models
- **THEN** the UI marks exactly one as default
- **AND** prevents deleting the last model or deleting the default without
  rotating it first

#### Scenario: Project runtime settings show inheritance

- **WHEN** a user views runtime settings for a project
- **THEN** each slot shows whether it inherits the global default or uses a
  project override
- **AND** the UI provides a reset-to-global action for overridden slots
- **AND** project override controls do not ask for provider API keys
- **AND** project override model controls are selectors, not free-text model ID
  fields

### Requirement: Frontend polish is workflow-first

The frontend MUST present the existing local product workflows as a coherent
workspace instead of a marketing landing page or a collection of disconnected
demos.

#### Scenario: Product workspace is the first screen

- **WHEN** a user opens the frontend
- **THEN** the first useful screen gives access to project context, authoring,
  ingestion, chat, history and observability workflows
- **AND** it does not require the user to pass through a marketing landing page
  before doing product work

#### Scenario: Workflow navigation preserves project context

- **WHEN** a user selects or creates a project
- **THEN** authoring, ingestion, chat, history and observability surfaces reuse
  the same project context
- **AND** changing workflow views does not silently clear valid project/source
  inputs or chat draft text

### Requirement: Frontend polish covers operational states

The frontend MUST include user-visible states for the normal and failure paths
of authoring, ingestion, chat, history and observability.

#### Scenario: Requests expose stable states

- **WHEN** a frontend request is empty, loading, successful, rejected by HTTP
  validation or blocked by network/backend unavailability
- **THEN** the UI shows a clear state for that condition
- **AND** preserves valid user input when the request fails

#### Scenario: Streaming and ingestion expose in-progress states

- **WHEN** chat streaming or ingestion work is in progress
- **THEN** the UI exposes progress, cancellation or retry affordances according
  to the existing public contracts
- **AND** it does not invent a successful chat answer, citation or ingestion
  result when the backend did not return one

### Requirement: Frontend retrieval polish follows dense_sparse default

The frontend MUST follow the backend `dense_sparse` default retrieval
experience and MUST NOT promote other advanced retrieval modes into the default
UI.

#### Scenario: Default chat uses dense_sparse retrieval

- **WHEN** a user sends a normal chat question without selecting experimental
  controls
- **THEN** the frontend uses the backend default retrieval strategy
- **AND** the backend default is `dense_sparse`

#### Scenario: Advanced modes are not default controls

- **WHEN** M32 frontend polish is implemented
- **THEN** `contextual_dense`, `lexical`, `hybrid_rrf`, `dense_rerank` and
  `graph` are not presented as default product controls
- **AND** any later exposure is opt-in, clearly experimental and consistent
  with M31 strategy-gate decisions

### Requirement: Frontend polish has visual QA criteria

The frontend MUST define visual and interaction QA criteria before M32 is
closed.

#### Scenario: Responsive QA is required

- **WHEN** a M32 implementation slice changes frontend screens
- **THEN** the slice validates affected workflows on desktop and mobile
  viewports
- **AND** checks for console errors, broken layout, overlapping text and
  unreadable controls before the slice is considered complete

#### Scenario: Documentation follows user-facing workflow changes

- **WHEN** frontend polish changes the local first-run or dev workflow
- **THEN** the affected README or runbook instructions are updated in the same
  milestone sequence
