# product-authoring-surface Specification

## Purpose
TBD - created by archiving change m23-product-authoring-surface. Update Purpose after archive.
## Requirements
### Requirement: Projects are authored through public surfaces

The system MUST let authorized users create, list and inspect projects without
direct SQL, private fixtures or test helpers. Project creation is restricted to
`superadmin`; project listing remains available to authenticated users as a
discovery surface.

#### Scenario: Superadmin creates a dense_sparse project

- **GIVEN** the current user is `superadmin`
- **WHEN** they create a project through API, CLI or frontend
- **THEN** the project is persisted with a stable `id`
- **AND** `embedding_mode` defaults to `dense_sparse`
- **AND** `retrieval_contextualization_enabled` defaults according to the
  existing domain contract
- **AND** the response includes public project fields without provider secrets

#### Scenario: Non-superadmin cannot create project

- **GIVEN** the current user is not `superadmin`
- **WHEN** they create a project through API, CLI or frontend
- **THEN** the operation is rejected with a stable authorization error
- **AND** no project row is created

#### Scenario: User lists projects deterministically with access status

- **WHEN** an authenticated user lists projects through API, CLI or frontend
- **THEN** the results are ordered deterministically
- **AND** each item includes public project fields, effective role and access
  status for the current user
- **AND** no provider secrets, API keys or internal connection settings are
  returned

#### Scenario: Missing or locked project is explicit

- **WHEN** a user asks for a project id that does not exist
- **THEN** API returns 404
- **AND** CLI exits non-zero with a stable user-facing error
- **AND** frontend preserves input state and shows an error state

- **WHEN** a user asks for a project id that exists but is not accessible to
  them
- **THEN** project-scoped tool routes return a stable access error
- **AND** do not return project-private data

### Requirement: Sources are authored within a project

The system MUST let users with project role `contributor` or higher create,
list and inspect sources for an existing accessible project without direct SQL,
private fixtures or test helpers.

#### Scenario: Contributor creates a text source

- **GIVEN** the current user has project role `contributor` or `admin`
- **WHEN** they create a `markdown`, `text` or `txt` source
- **THEN** the source is persisted under the requested `project_id`
- **AND** the request requires non-empty text content that is persisted in
  `extra_metadata.content`

#### Scenario: Viewer cannot create source directly

- **GIVEN** the current user has project role `viewer`
- **WHEN** they create a source directly
- **THEN** the request is rejected
- **AND** they can only propose knowledge through the proposal flow

#### Scenario: Source reads stay project-scoped and access-scoped

- **WHEN** a user lists or gets sources for an accessible project
- **THEN** only sources belonging to that `project_id` are returned
- **AND** a source id from another project is treated as not found
- **AND** a source in a locked project is not returned

### Requirement: Authoring does not run ingestion jobs

The system MUST keep M23 authoring separate from ingestion operations and job
state.

#### Scenario: Creating a source does not enqueue ingestion

- **WHEN** a user creates a source through API, CLI or frontend
- **THEN** no `ingest_source` job is created by the authoring operation
- **AND** no document versions, chunks or embeddings are created by the
  authoring operation
- **AND** the next step for ingestion remains an explicit M24 operation

#### Scenario: Unsupported source type is rejected early

- **WHEN** a user submits a source type outside `markdown`, `text`, `txt` or
  `url`
- **THEN** the authoring surface rejects it before persistence
- **AND** the error names the supported source types

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

