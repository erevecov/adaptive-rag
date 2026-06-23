# Delta for chat-frontend

## ADDED Requirements

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
