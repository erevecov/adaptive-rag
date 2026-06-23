# Delta for chat-frontend

## ADDED Requirements

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
