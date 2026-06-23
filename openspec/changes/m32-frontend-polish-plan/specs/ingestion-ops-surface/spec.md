## ADDED Requirements

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
