## ADDED Requirements

### Requirement: Retrieval surface exposes dense_sparse strategy opt-in

The system MUST expose `strategy=dense_sparse` for API, CLI and offline evals
without changing the default retrieval strategy.

#### Scenario: dense_sparse fuses dense and sparse candidates

- **WHEN** retrieval is requested with `strategy=dense_sparse`
- **THEN** the service runs dense retrieval and sparse retrieval over the same
  query, project and filters
- **AND** deduplicates candidates by chunk id
- **AND** applies reciprocal rank fusion
- **AND** records dense rank, sparse rank and RRF score in result metadata

#### Scenario: dense remains default

- **WHEN** no retrieval strategy is supplied by API, CLI, chat or eval callers
- **THEN** retrieval uses `strategy=dense`
- **AND** sparse retrieval never runs implicitly

#### Scenario: Sparse backfill is explicit

- **WHEN** a user wants sparse retrieval coverage for a project
- **THEN** they run an explicit sparse backfill command for that project
- **AND** the command reports embedded, reused and total chunk counts
