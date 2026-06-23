# product-authoring-surface Specification

## Purpose
TBD - created by archiving change m23-product-authoring-surface. Update Purpose after archive.
## Requirements
### Requirement: Projects are authored through public surfaces

The system MUST let a local user create, list and inspect projects without
direct SQL, private fixtures or test helpers.

#### Scenario: User creates a dense project

- **WHEN** a user creates a project through API, CLI or frontend
- **THEN** the project is persisted with a stable `id`
- **AND** `embedding_mode` defaults to `dense`
- **AND** `retrieval_contextualization_enabled` defaults according to the
  existing domain contract
- **AND** the response includes `id`, `name`, `embedding_mode`,
  `retrieval_contextualization_enabled`, `budget_config_json`, `created_at` and
  `updated_at`

#### Scenario: User lists projects deterministically

- **WHEN** a user lists projects through API, CLI or frontend
- **THEN** the results are ordered deterministically
- **AND** each item uses the same public project response shape
- **AND** no provider secrets, API keys or internal connection settings are
  returned

#### Scenario: Missing project is explicit

- **WHEN** a user asks for a project id that does not exist
- **THEN** API returns 404
- **AND** CLI exits non-zero with a stable user-facing error
- **AND** frontend preserves input state and shows an error state

### Requirement: Sources are authored within a project

The system MUST let a local user create, list and inspect sources for an
existing project without direct SQL, private fixtures or test helpers.

#### Scenario: User creates a text source

- **WHEN** a user creates a `markdown`, `text` or `txt` source
- **THEN** the source is persisted under the requested `project_id`
- **AND** the request requires non-empty text content that is persisted in
  `extra_metadata.content`
- **AND** the response includes `id`, `project_id`, `source_type`,
  `external_id`, `tags`, `extra_metadata`, `created_at` and `updated_at`

#### Scenario: User creates a URL source

- **WHEN** a user creates a `url` source
- **THEN** the source is persisted under the requested `project_id`
- **AND** `external_id` stores the submitted URL
- **AND** authoring does not fetch the URL or run ingestion

#### Scenario: Duplicate source identity is handled

- **WHEN** a user creates a source with an existing `(project_id, source_type,
  external_id)`
- **THEN** API returns a stable conflict response
- **AND** CLI exits non-zero with a stable duplicate-source message
- **AND** frontend shows the failure without clearing valid project/source
  inputs

#### Scenario: Source reads stay project-scoped

- **WHEN** a user lists or gets sources for a project
- **THEN** only sources belonging to that `project_id` are returned
- **AND** a source id from another project is treated as not found

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

