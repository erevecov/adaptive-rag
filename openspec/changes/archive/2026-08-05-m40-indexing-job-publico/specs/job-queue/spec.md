## ADDED Requirements

### Requirement: Worker can lease ingestion-family job types

The job repository/worker MUST support leasing the next ready job among a
declared set of job types so ingestion and indexing share one public worker loop.

#### Scenario: Lease prefers highest priority ready family job

- **WHEN** a project has queued `ingest_source` and `index_document_version` jobs
  ready to run
- **AND** the worker leases the next job for the ingestion family
- **THEN** selection uses existing priority / run_after / created_at ordering
- **AND** jobs of unrelated types (for example graph jobs) are not leased by
  that family worker
