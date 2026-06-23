## ADDED Requirements

### Requirement: Authoring polish keeps project and source work compact

The frontend authoring surface MUST let a local user create, select and inspect
projects and sources from a compact workspace without direct SQL or hidden
fixtures.

#### Scenario: Project selection drives the workspace

- **WHEN** a user creates or selects a project in the polished frontend
- **THEN** the selected project id is visible enough to orient the workflow
- **AND** downstream authoring, ingestion, chat, history and observability
  requests use that selected project

#### Scenario: Source authoring shows the next explicit step

- **WHEN** a user creates a supported source
- **THEN** the frontend shows that the source exists
- **AND** it does not claim that ingestion, indexing or chat readiness has
  happened until the public ingestion workflow reports it
- **AND** it offers the explicit ingestion next step when appropriate
