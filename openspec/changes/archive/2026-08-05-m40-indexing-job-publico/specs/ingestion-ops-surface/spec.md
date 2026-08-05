## ADDED Requirements

### Requirement: Run-next processes ingestion and indexing jobs

The public local `run-next` / worker operation MUST process the next ready job
among `ingest_source` and `index_document_version` for the project.

#### Scenario: Run-next indexes after ingest

- **WHEN** a project has a succeeded ingest that enqueued `index_document_version`
- **AND** a user runs `run-next` again (or the worker continues)
- **THEN** the indexing job is leased and processed
- **AND** the run response identifies the processed indexing job and document
  version
- **AND** chunks/embeddings for that version become available for retrieval

#### Scenario: Run-next is idle when neither job type is ready

- **WHEN** no queued `ingest_source` or `index_document_version` job is ready
- **THEN** the run response is `idle`

### Requirement: Indexing job state is inspectable like ingestion

The system MUST expose `index_document_version` jobs through the same list/detail
ingestion-ops surfaces as other project jobs.

#### Scenario: User lists indexing jobs

- **WHEN** a user lists ingestion jobs filtered by
  `job_type = index_document_version`
- **THEN** only indexing jobs for that project are returned
- **AND** each includes status, attempts, lock state and last error

## MODIFIED Requirements

### Requirement: Local ingestion can run explicitly

The system MUST expose a local operation to process the next queued ingestion
family job (`ingest_source` or `index_document_version`) without requiring
direct SQL.

#### Scenario: Run next processes a text source

- **WHEN** a queued `ingest_source` job references a text-like source
- **THEN** `run-next` processes it through `IngestionPipeline`
- **AND** creates or reuses the document version
- **AND** enqueues follow-up indexing work
- **AND** returns the processed job, source, document and document version ids

#### Scenario: Run next reports blocked jobs

- **WHEN** a queued ingestion-family job is blocked by a non-retryable error
- **THEN** the run response names the blocked job
- **AND** the job detail exposes `status = blocked` and `last_error`

#### Scenario: Run next is idle when no job is ready

- **WHEN** no queued ingestion-family job is ready for the project
- **THEN** the run response is `idle`
