## MODIFIED Requirements

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
