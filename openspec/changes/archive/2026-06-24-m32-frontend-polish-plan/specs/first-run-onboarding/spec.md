## ADDED Requirements

### Requirement: First-run polish connects setup to the frontend workspace

The first-run guidance MUST help a local user reach the polished frontend with
data that can produce cited chat answers.

#### Scenario: Empty workspace points to a local setup path

- **WHEN** the frontend has no selected project or no usable source data
- **THEN** it points the user toward the documented local setup path or public
  authoring and ingestion controls
- **AND** it does not require hosted provider credentials for the default path

#### Scenario: First-run report can seed the workspace

- **WHEN** a user runs `adaptive-rag first-run smoke`
- **THEN** the resulting project id can be reused in the frontend workspace
- **AND** the frontend can proceed to chat/history using public API contracts
  rather than fixtures or direct database access
