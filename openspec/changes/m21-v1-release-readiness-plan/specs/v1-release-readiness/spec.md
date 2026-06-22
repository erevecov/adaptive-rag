# Delta for v1-release-readiness

## ADDED Requirements

### Requirement: V1.0 release scope is explicit and conservative

The system MUST define a v1.0 release scope that reflects completed OpenSpec
capabilities and documented hold decisions before opening final release PRs.

#### Scenario: Scope reconciliation classifies original v1 items

- **WHEN** the v1.0 scope is reconciled after M20
- **THEN** each release item from `docs/architecture/v1-design.md` is classified
  as `in_v1`, `defer_post_v1` or `blocked`
- **AND** each deferred or blocked item records the decision source or missing
  evidence
- **AND** OpenSpec specs remain the authority when they conflict with the older
  design baseline

#### Scenario: Held retrieval strategies do not enter by inertia

- **WHEN** lexical/RRF, Qwen sparse retrieval, graph defaults or candidate
  tuning defaults are considered for v1.0
- **THEN** they remain out of scope unless a current OpenSpec change provides
  evidence that satisfies the retrieval-quality and graph-store gates
- **AND** dense retrieval remains the default release path

### Requirement: Readiness audit separates core completion from release package

The system MUST measure v1.0 readiness as a release checklist, not as another
open-ended feature backlog.

#### Scenario: Readiness status uses bounded categories

- **WHEN** the readiness audit is updated
- **THEN** each item is marked `done`, `needs_release_work`, `deferred` or
  `blocked`
- **AND** the audit separates product core, packaging, docs, demo evidence and
  validation gates
- **AND** the percentage estimate is derived from that bounded checklist

#### Scenario: Final PR sequence stays small

- **WHEN** readiness work is planned
- **THEN** it is split into small PRs for scope reconciliation, local package,
  demo/reporting and release quality gate
- **AND** runtime feature work is not mixed into the planning PR

### Requirement: Release package is local-first and reproducible

The system MUST provide a v1.0 release path that a reviewer can run locally
without mandatory hosted services beyond optional provider smokes.

#### Scenario: Local stack documents required services

- **WHEN** the release package is prepared
- **THEN** it documents how to run API, worker and Postgres/pgvector locally
- **AND** optional services such as Neo4j, hosted Qwen, graph retrieval, voice
  and observability exporters are not required for the default release path

#### Scenario: Portfolio demo produces reproducible evidence

- **WHEN** the demo or release report is executed
- **THEN** it produces deterministic or clearly bounded artifacts for retrieval,
  chat, eval quality, cost and latency
- **AND** any hosted-provider step is opt-in, budgeted and safe to skip without
  invalidating the offline release gate

#### Scenario: Release gate leaves no active OpenSpec changes

- **WHEN** v1.0 is ready for manual tag or release
- **THEN** OpenSpec has no active changes
- **AND** canonical specs, roadmap and progress docs reflect the released scope
- **AND** frontend, Python, CLI smokes, OpenSpec validation and release
  documentation checks have passed
