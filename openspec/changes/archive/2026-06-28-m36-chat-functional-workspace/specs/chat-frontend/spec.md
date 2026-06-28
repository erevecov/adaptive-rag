## ADDED Requirements

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

The frontend MUST expose a Settings / Appearance module where the user can pick
one global interface theme, following an app-wide pattern of `data-theme`,
dark-variant classing and local persistence.

#### Scenario: Settings exposes the three supported themes

- **WHEN** the user opens the Settings workspace view
- **THEN** the frontend renders Light, Dark and Purple theme options as
  selectable cards with swatch previews
- **AND** the active card is marked with `aria-pressed=true`
- **AND** no additional unsupported theme option is rendered

#### Scenario: Theme changes apply to every workspace view

- **WHEN** the user selects a theme from Settings
- **THEN** the selected theme is applied to the document root as `data-theme`
- **AND** dark variants also carry the document root `.dark` class
- **AND** the selection is saved to local storage
- **AND** Chat, Authoring, Observability, Runtime and Settings use the same
  selected theme instead of tab-scoped palettes

#### Scenario: Persisted theme hydrates before interaction

- **WHEN** a valid theme id is already stored locally
- **THEN** the app hydrates with that theme selected
- **AND** invalid or missing values fall back to the default Purple theme
