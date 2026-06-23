## MODIFIED Requirements

### Requirement: Release package is local-first and reproducible

The system MUST provide a v1.0 release path that a reviewer can run locally
without mandatory hosted services beyond optional provider smokes.

#### Scenario: Local stack documents required services

- **WHEN** the release package is prepared
- **THEN** it documents how to run API, worker and Postgres/pgvector locally
- **AND** optional services such as Neo4j, hosted Qwen, graph retrieval, voice
  and observability exporters are not required for the default release path

#### Scenario: Product demo produces reproducible evidence

- **WHEN** the demo or release report is executed
- **THEN** it produces deterministic or clearly bounded artifacts for
  user-created project/source ingestion, retrieval, chat, eval quality, cost
  and latency
- **AND** any hosted-provider step is opt-in, budgeted and safe to skip without
  invalidating the offline release gate

#### Scenario: Release gate leaves no active OpenSpec changes

- **WHEN** v1.0 is ready for manual tag or release
- **THEN** OpenSpec has no active changes
- **AND** canonical specs, roadmap and progress docs reflect the finished
  product scope
- **AND** frontend, Python, CLI smokes, OpenSpec validation and release
  documentation checks have passed

#### Scenario: Final quality gate emits release decision

- **WHEN** `adaptive-rag v1 quality-gate` completes successfully
- **THEN** it emits `release_decision` as `ready_for_v1_0`
- **AND** it includes passed criteria for product flow, ingestion job state,
  indexing, cited chat, public follow-up commands and opt-in boundaries
- **AND** it records that a git tag or GitHub release remains a manual action
