# ingestion-ops-surface Specification

## Purpose
TBD - created by archiving change m24-ingestion-ops-surface. Update Purpose after archive.
## Requirements
### Requirement: Sources can be queued for ingestion publicly

The system MUST let a local user enqueue document ingestion for a project source
through public API, CLI and frontend surfaces.

#### Scenario: User enqueues a source ingestion job

- **WHEN** a user requests ingestion for a source in the selected project
- **THEN** the system creates a job with `job_type = ingest_source`
- **AND** the payload stores the requested `source_id`
- **AND** the job starts with `status = queued`
- **AND** no document versions, chunks or embeddings are created by enqueueing
  alone

#### Scenario: Missing source is explicit

- **WHEN** a user requests ingestion for a source id that does not belong to the
  project
- **THEN** API returns 404
- **AND** CLI exits non-zero with `source not found`
- **AND** frontend preserves valid form state and shows the error

### Requirement: Ingestion jobs are inspectable

The system MUST expose job state and job events for project-scoped ingestion
operations.

#### Scenario: User lists ingestion jobs

- **WHEN** a user lists ingestion jobs for a project
- **THEN** jobs are returned in deterministic order
- **AND** each job includes status, attempts, max attempts, run time, lock state
  and last error
- **AND** jobs from other projects are not returned

#### Scenario: User inspects job detail

- **WHEN** a user opens a job detail
- **THEN** the response includes the job payload and append-only events
- **AND** event order is deterministic

### Requirement: Local ingestion can run explicitly

The system MUST expose a local operation to process the next queued
`ingest_source` job without requiring direct SQL.

#### Scenario: Run next processes a text source

- **WHEN** a queued `ingest_source` job references a text-like source
- **THEN** `run-next` processes it through `IngestionPipeline`
- **AND** creates or reuses the document version
- **AND** returns the processed job, source, document and document version ids

#### Scenario: Run next reports blocked jobs

- **WHEN** a queued `ingest_source` job is blocked by a non-retryable ingestion
  error
- **THEN** the run response names the blocked job
- **AND** the job detail exposes `status = blocked` and `last_error`

#### Scenario: Run next is idle when no job is ready

- **WHEN** no queued `ingest_source` job is ready for the project
- **THEN** the run response is `idle`

### Requirement: Failed ingestion can be retried explicitly

The system MUST let a local user requeue ingestion jobs that are `blocked` or
`dead_letter`.

#### Scenario: User retries a blocked job

- **WHEN** a user retries a `blocked` ingestion job
- **THEN** the job returns to `queued`
- **AND** lock and last error fields are cleared
- **AND** a retry event is appended

#### Scenario: Non-retryable status is rejected

- **WHEN** a user retries a `queued`, `running` or `succeeded` job
- **THEN** the operation fails with `job is not retryable`

### Requirement: Ingestion polish makes job state actionable

The frontend ingestion surface MUST make local ingestion state understandable
and actionable using the existing public job contracts.

#### Scenario: Job list communicates operational status

- **WHEN** a user views ingestion jobs for the selected project
- **THEN** each job exposes its status, attempts, timing/lock state when
  available and last error when present
- **AND** queued, running, succeeded, blocked and dead-letter states are visually
  distinguishable

#### Scenario: Retry controls follow backend retryability

- **WHEN** a job is `blocked` or `dead_letter`
- **THEN** the frontend may offer retry controls backed by the public retry
  contract
- **AND** jobs in non-retryable states do not present retry as an available
  action

#### Scenario: Run-next result is explicit

- **WHEN** a user runs the next ingestion job from the frontend
- **THEN** the UI reports whether the backend returned processed, blocked or
  idle
- **AND** it does not treat idle or blocked as successful indexing
