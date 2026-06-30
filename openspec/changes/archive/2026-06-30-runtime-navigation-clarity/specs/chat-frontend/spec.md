## MODIFIED Requirements

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

## ADDED Requirements

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
