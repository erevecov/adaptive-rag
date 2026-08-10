# product-authoring-surface Specification

## Purpose
TBD - created by archiving change m23-product-authoring-surface. Update Purpose after archive.
## Requirements
### Requirement: Workspaces are authored through public surfaces

The system MUST let authorized users create, list and inspect workspaces without
direct SQL, private fixtures or test helpers. Workspace creation is restricted to
`superadmin`; workspace listing remains available to authenticated users as a
discovery surface.

#### Scenario: Superadmin creates a dense_sparse workspace

- **GIVEN** the current user is `superadmin`
- **WHEN** they create a workspace through API, CLI or frontend
- **THEN** the workspace is persisted with a stable `id`
- **AND** `embedding_mode` defaults to `dense_sparse`
- **AND** `retrieval_contextualization_enabled` defaults according to the
  existing domain contract
- **AND** the response includes public workspace fields without provider secrets

#### Scenario: Non-superadmin cannot create workspace

- **GIVEN** the current user is not `superadmin`
- **WHEN** they create a workspace through API, CLI or frontend
- **THEN** the operation is rejected with a stable authorization error
- **AND** no workspace row is created

#### Scenario: User lists workspaces deterministically with access status

- **WHEN** an authenticated user lists workspaces through API, CLI or frontend
- **THEN** the results are ordered deterministically
- **AND** each item includes public workspace fields, effective role and access
  status for the current user
- **AND** no provider secrets, API keys or internal connection settings are
  returned

#### Scenario: Missing or locked workspace is explicit

- **WHEN** a user asks for a workspace id that does not exist
- **THEN** API returns 404
- **AND** CLI exits non-zero with a stable user-facing error
- **AND** frontend preserves input state and shows an error state

- **WHEN** a user asks for a workspace id that exists but is not accessible to
  them
- **THEN** workspace-scoped tool routes return a stable access error
- **AND** do not return workspace-private data

### Requirement: Sources are authored within a workspace

The system MUST let users with workspace role `contributor` or higher create,
list and inspect sources for an existing accessible workspace without direct SQL,
private fixtures or test helpers.

#### Scenario: Contributor creates a text source

- **GIVEN** the current user has workspace role `contributor` or `admin`
- **WHEN** they create a `markdown`, `text` or `txt` source
- **THEN** the source is persisted under the requested `workspace_id`
- **AND** the request requires non-empty text content that is persisted in
  `extra_metadata.content`

#### Scenario: Viewer cannot create source directly

- **GIVEN** the current user has workspace role `viewer`
- **WHEN** they create a source directly
- **THEN** the request is rejected
- **AND** they can only propose knowledge through the proposal flow

#### Scenario: Source reads stay workspace-scoped and access-scoped

- **WHEN** a user lists or gets sources for an accessible workspace
- **THEN** only sources belonging to that `workspace_id` are returned
- **AND** a source id from another workspace is treated as not found
- **AND** a source in a locked workspace is not returned

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

- **WHEN** a user submits a source type outside `markdown`, `text`, `txt`,
  `url`, `pdf` or `docx`
- **THEN** the authoring surface rejects it before persistence
- **AND** the error names the supported source types

#### Scenario: PDF and DOCX sources require base64 payload

- **WHEN** a user creates a source with type `pdf` or `docx`
- **AND** `extra_metadata.content_base64` is missing, empty, not valid base64,
  or decodes to more than the configured max bytes
- **THEN** the authoring surface rejects it before persistence with a stable
  validation error

#### Scenario: PDF and DOCX sources accept valid base64 payload

- **WHEN** a user creates a source with type `pdf` or `docx`
- **AND** `extra_metadata.content_base64` decodes to non-empty bytes within the
  size limit
- **THEN** the source is persisted
- **AND** no ingestion job is created by authoring alone

### Requirement: Authoring polish keeps workspace and source work compact

The frontend authoring surface MUST let a local user create, select and inspect
workspaces and sources from a compact workspace without direct SQL or hidden
fixtures.

#### Scenario: Workspace selection drives the workspace

- **WHEN** a user creates or selects a workspace in the polished frontend
- **THEN** the selected workspace id is visible enough to orient the workflow
- **AND** downstream authoring, ingestion, chat, history and observability
  requests use that selected workspace

#### Scenario: Source authoring shows the next explicit step

- **WHEN** a user creates a supported source
- **THEN** the frontend shows that the source exists
- **AND** it does not claim that ingestion, indexing or chat readiness has
  happened until the public ingestion workflow reports it
- **AND** it offers the explicit ingestion next step when appropriate

### Requirement: Workspaces can be updated and soft-deleted

The system MUST allow authorized clients to rename workspaces and soft-delete them
so removed workspaces leave the default list while remaining auditable.

#### Scenario: Admin renames workspace

- **WHEN** a workspace admin PATCHes a workspace name
- **THEN** the workspace name is updated

#### Scenario: Superadmin soft-deletes workspace

- **WHEN** a superadmin DELETEs a workspace
- **THEN** the workspace gains `deleted_at`
- **AND** subsequent GET/list omit it

### Requirement: Sources can be updated and soft-deleted with index cascade

The system MUST allow authorized clients to update source metadata and soft-delete
sources, cascading removal of searchable index rows for that source.

#### Scenario: Contributor updates source metadata

- **WHEN** a contributor PATCHes source tags or content metadata
- **THEN** the source is updated

#### Scenario: Admin soft-deletes source and cascades index

- **WHEN** a workspace admin DELETEs a source
- **THEN** the source is soft-deleted
- **AND** documents/chunks/embeddings for that source are removed

