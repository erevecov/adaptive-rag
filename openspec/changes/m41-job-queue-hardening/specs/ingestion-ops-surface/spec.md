## ADDED Requirements

### Requirement: Failure and recovery events are inspectable

Ingestion ops job detail MUST expose lease recovery and failure events produced
by the hardened worker path.

#### Scenario: User inspects a recovered or failed job

- **WHEN** a job was released after lease expiry or failed via `fail()`
- **THEN** job detail includes the corresponding `released`, `failed_attempt`
  or `dead_lettered` events in deterministic order
- **AND** `last_error` is visible when present
