# chat-frontend Specification

## MODIFIED Requirements

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
