# Delta for job-queue

## ADDED Requirements

### Requirement: Jobs can be listed and manually requeued

The job repository MUST support public ingestion operations without forcing
callers to write SQL.

#### Scenario: Jobs are listed deterministically

- **WHEN** API or CLI lists jobs for a project
- **THEN** `JobRepository` returns project-scoped jobs ordered by creation time
  and id
- **AND** optional filters can narrow by status and job type

#### Scenario: Blocked or dead-letter jobs are requeued manually

- **WHEN** API or CLI retries a `blocked` or `dead_letter` job
- **THEN** `JobRepository` moves it to `queued`
- **AND** clears `locked_by`, `locked_until` and `last_error`
- **AND** appends a `retried` event
