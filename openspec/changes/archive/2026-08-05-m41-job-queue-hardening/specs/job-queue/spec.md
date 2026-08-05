## ADDED Requirements

### Requirement: Worker recovers expired leases before leasing

The public ingestion-family worker MUST release expired running leases for the
project before selecting the next job.

#### Scenario: Expired running job becomes leaseable again

- **WHEN** a job is `running` with `locked_until <= now`
- **AND** a worker runs the next ingestion-family cycle for that project
- **THEN** the system releases the expired lease back to `queued`
- **AND** appends a `released` event
- **AND** the job may be leased again by a subsequent worker cycle

### Requirement: Unexpected job failures use fail with backoff

The worker MUST route unexpected exceptions through `JobRepository.fail()` so
retries and dead-letter are real, not stuck `running` rows.

#### Scenario: Unexpected error requeues with backoff while attempts remain

- **WHEN** a leased job raises an unexpected exception and `attempts < max_attempts`
- **THEN** the job returns to `queued` via `fail()`
- **AND** `run_after` is set in the future according to backoff
- **AND** `last_error` stores the error message
- **AND** a `failed_attempt` event is recorded

#### Scenario: Unexpected error dead-letters when attempts are exhausted

- **WHEN** a leased job raises an unexpected exception and `attempts >= max_attempts`
- **THEN** the job status becomes `dead_letter`
- **AND** a `dead_lettered` event is recorded
- **AND** the job is not left in `running`
