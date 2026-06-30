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

#### Scenario: Runtime settings are separated into named submodules

- **WHEN** a user opens Settings > Runtime
- **THEN** the UI exposes `Connections`, `Model catalog`, `Global defaults`
  and `Project overrides` as separate Runtime submodules
- **AND** each submodule renders only the controls and data for that concern
- **AND** the UI does not render a generic `Refresh runtime` button

#### Scenario: User manages global provider connections

- **WHEN** a user opens Runtime > Connections
- **THEN** the UI can list configured provider connections, readiness status
  and supported slot capabilities
- **AND** hosted and local connections can both be visible at the same time
- **AND** no plaintext API key, ciphertext or Authorization header is rendered
- **AND** creating a connection does not ask the user to type an internal
  connection ID

#### Scenario: User saves or rotates a provider secret

- **WHEN** a user enters a provider secret in Runtime > Connections
- **THEN** the frontend sends it only to the backend save/rotate endpoint
- **AND** clears the input after success or failure
- **AND** subsequent reads show only safe status such as configured time or
  non-reversible fingerprint
- **AND** the connection target is selected from existing connections

#### Scenario: User syncs the provider model catalog

- **WHEN** a user opens Runtime > Model catalog
- **THEN** the UI shows a connection selector, a `Sync models` action and the
  persisted provider model catalog
- **AND** model sync is scoped to the selected connection

#### Scenario: User configures fixed global slots

- **WHEN** a user opens Runtime > Global defaults
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

- **WHEN** a user opens Runtime > Project overrides
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
  ingestion, chat, history, runtime and observability workflows
- **AND** it does not require the user to pass through a marketing landing page
  before doing product work

#### Scenario: Workflow navigation preserves project context

- **WHEN** a user selects or creates a project
- **THEN** authoring, ingestion, chat, history, runtime and observability
  surfaces reuse the same project context
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

### Requirement: Frontend uses a searchable project selector with access states

The frontend MUST replace manual project id entry with project discovery that
shows accessible and locked projects.

#### Scenario: Selector shows all project names

- **GIVEN** the project list API returns accessible and locked projects
- **WHEN** the app renders the project selector
- **THEN** all project names are searchable
- **AND** locked projects are visually disabled or marked unavailable
- **AND** locked projects cannot be selected for chat, authoring or ingestion

#### Scenario: Accessible project drives workspace requests

- **WHEN** the user selects an accessible project
- **THEN** chat, session history, source viewer, authoring, ingestion,
  observability and runtime override requests use that project id
- **AND** stale selected sessions from a previous project are cleared

### Requirement: Frontend gates surfaces by effective role

The frontend MUST use the current user's effective role to show only usable
project surfaces while relying on backend authorization as source of truth.

#### Scenario: Viewer sees chat and proposal actions

- **GIVEN** the current user has project role `viewer`
- **WHEN** they open an accessible project
- **THEN** chat is available
- **AND** direct source authoring, ingestion controls, member management and
  knowledge review queue are hidden or disabled
- **AND** proposing knowledge from chat is available

#### Scenario: Contributor sees knowledge review

- **GIVEN** the current user has project role `contributor`
- **WHEN** they open an accessible project
- **THEN** direct source authoring and knowledge review queue are available
- **AND** project member management remains unavailable

#### Scenario: Admin sees project member management

- **GIVEN** the current user has project role `admin`
- **WHEN** they open an accessible project
- **THEN** project member management is available
- **AND** project archive/delete controls are unavailable unless the user is
  also `superadmin`

#### Scenario: Superadmin sees global administration

- **GIVEN** the current user has system role `superadmin`
- **WHEN** they open admin settings
- **THEN** global user management and project creation are available
- **AND** provider secret values are still not shown in the browser

### Requirement: Frontend supports knowledge proposal review

The frontend MUST let contributor-or-higher users review pending chat-sourced
knowledge proposals.

#### Scenario: Reviewer approves proposal

- **GIVEN** a pending proposal exists for the selected project
- **WHEN** a contributor approves it from the review queue
- **THEN** the row updates to approved
- **AND** the UI shows the source or ingestion job created by the backend when
  returned

#### Scenario: Reviewer refines proposal

- **GIVEN** a pending proposal exists
- **WHEN** a contributor edits the proposed text and saves refinement
- **THEN** the refined text is shown as the text that will be approved
- **AND** the original proposal remains visible for context

#### Scenario: Reviewer rejects proposal with reason

- **GIVEN** a pending proposal exists
- **WHEN** a contributor rejects it
- **THEN** the UI requires a non-empty reason
- **AND** removes or marks the item as rejected after the backend confirms

### Requirement: Chat workspace uses functional session navigation

The frontend MUST expose chat sessions as a navigable workspace surface backed
by public chat history APIs.

#### Scenario: Workspace shell follows chat-first information architecture

- **WHEN** the user opens the chat workspace on a desktop viewport
- **THEN** the surface separates session navigation, chat composition and
  response content, and inspection context into distinct left, center and right
  regions
- **AND** the right inspector exposes Context and Minimap tabs without removing
  the underlying functional session, audit or source contracts
- **AND** mobile or narrow viewports collapse without horizontal overflow and
  keep the chat composer before secondary session and inspector panels

#### Scenario: Session navigation uses real status filters

- **WHEN** a user selects a chat session filter such as all, running,
  succeeded or failed
- **THEN** the frontend calls `GET /projects/{project_id}/chat/sessions` with
  only supported public query parameters
- **AND** the visible sessions come from the API response
- **AND** no archived-session state is shown unless a public archive contract
  exists

#### Scenario: Selecting a session loads durable detail

- **WHEN** the user selects a session from navigation
- **THEN** the frontend calls
  `GET /projects/{project_id}/chat/sessions/{session_id}`
- **AND** messages, tool calls, retrieval runs, retrieved chunks and provider
  usage are rendered read-only from that response
- **AND** the frontend does not replay chat, retrieval or providers

### Requirement: Chat workspace shows context and usage from audit data

The frontend MUST summarize context, model, usage, cost, tokens and latency from
existing chat audit and observability data.

#### Scenario: Selected-session usage is summarized

- **WHEN** a selected session has provider usage records
- **THEN** the context panel shows operation, provider, model, status, known
  tokens, estimated cost and latency values from the selected session detail
- **AND** unknown or missing values remain visible as unknown
- **AND** no values are invented from absent provider fields

#### Scenario: Project observability is optional and isolated

- **WHEN** project observability summary data is loaded
- **THEN** the context panel can show project-level session totals, provider
  usage totals, known cost and status breakdowns
- **AND** observability loading or failure does not clear the selected chat
  session

### Requirement: Chat workspace provides minimap and action stepper

The frontend MUST make persisted conversation and internal action data
navigable without changing backend behavior.

#### Scenario: Conversation minimap navigates persisted messages

- **WHEN** a selected session has persisted messages
- **THEN** the minimap renders one item per message using its role and content
  preview
- **AND** activating an item navigates focus to the corresponding message in
  the session detail

#### Scenario: Action stepper renders stored internals

- **WHEN** a selected session has tool calls, retrieval runs, retrieved chunks
  or provider usage
- **THEN** the stepper renders ordered read-only steps for those records
- **AND** each step shows status, latency, cost, tokens, rank or scores when
  present
- **AND** the stepper does not re-run chat, retrieval or providers

### Requirement: Chat workspace exposes functional source inspection

The frontend MUST let users inspect citation/source details through existing
public source contracts when enough citation metadata is available.

#### Scenario: Citation or retrieved chunk opens source viewer

- **WHEN** the user opens a current response citation or persisted retrieved
  chunk whose metadata includes `source_id`
- **THEN** the frontend calls `GET /projects/{project_id}/sources/{source_id}`
- **AND** renders source type, external id, tags, sync metadata and citation
  snippet
- **AND** lookup failure preserves the citation metadata and shows an isolated
  source viewer error

### Requirement: STT and memory are not fake UI

The frontend MUST only expose speech-to-text or memory surfaces when backed by a
verified functional path.

#### Scenario: STT uses a real contract or progressive fallback

- **WHEN** STT is implemented
- **THEN** Qwen-backed STT requires current provider documentation, a backend
  contract and tests
- **AND** browser speech recognition fallback must show unsupported and error
  states
- **AND** transcribed text populates the chat question field without exposing
  provider secrets in the browser

#### Scenario: Memory is deferred without durable storage

- **WHEN** no durable memory contract or verified preference source exists
- **THEN** the frontend does not render fake memory state
- **AND** the limitation is documented as deferred work

### Requirement: Appearance themes are global and configurable

The frontend MUST expose a My account / Appearance module where the user can
pick one global interface theme, following an app-wide pattern of `data-theme`,
dark-variant classing and local persistence.

#### Scenario: My account exposes the three supported themes

- **WHEN** the user opens the My account workspace and selects the Appearance
  module
- **THEN** the frontend renders Light, Dark and Purple theme options as
  selectable cards with swatch previews
- **AND** the active card is marked with `aria-pressed=true`
- **AND** no additional unsupported theme option is rendered

#### Scenario: Theme changes apply to every workspace view

- **WHEN** the user selects a theme from My account > Appearance
- **THEN** the selected theme is applied to the document root as `data-theme`
- **AND** dark variants also carry the document root `.dark` class
- **AND** the selection is saved to local storage
- **AND** Chat, Authoring, Observability, Runtime and Settings use the same
  selected theme instead of module-scoped palettes

#### Scenario: Persisted theme hydrates before interaction

- **WHEN** a valid theme id is already stored locally
- **THEN** the app hydrates with that theme selected
- **AND** invalid or missing values fall back to the default Purple theme

### Requirement: Sidebar navigation is contextual

The frontend MUST use the left sidebar as contextual navigation for the active
primary area.

#### Scenario: Chat keeps session navigation

- **WHEN** the user selects `Chat`
- **THEN** the sidebar shows chat session creation, filters and session rows
- **AND** selecting a session still loads durable chat session detail

#### Scenario: My account shows account modules

- **WHEN** the user selects `My account`
- **THEN** the sidebar shows account modules including `Appearance`
- **AND** the sidebar does not show chat sessions
- **AND** unavailable modules such as `Memory` are clearly disabled or deferred
  unless backed by a durable contract

#### Scenario: Settings shows modules and submodules

- **WHEN** the user selects `Settings`
- **THEN** the sidebar shows `Authoring`, `Observability` and `Runtime`
- **AND** each settings module exposes its submodules in the sidebar
- **AND** the sidebar does not show chat sessions
- **AND** the main content matches the selected sidebar submodule
