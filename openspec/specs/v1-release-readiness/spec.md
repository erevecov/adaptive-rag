# v1-release-readiness Specification

## Purpose
Documentar el contrato de readiness de v1.0 despues del reset M22: M21 cuenta
como evidencia de core/pre-v1, pero el release final depende de
`v1-product-completion`, paquete local-first reproducible, demo de producto y
gate final sin changes OpenSpec activos.
## Requirements
### Requirement: V1.0 release scope is explicit and conservative

The system MUST define release scope against the current product-completion
contract before opening final release PRs. M21 scope reconciliation is retained
as core/pre-v1 evidence, not as the final v1.0 product boundary.

#### Scenario: Scope reconciliation classifies original v1 items

- **WHEN** the v1.0 scope is reconciled after M20
- **THEN** each release item from `docs/architecture/v1-design.md` is
  classified as `in_core_pre_v1`, `product_gap`, `defer_post_v1` or `blocked`
- **AND** each deferred, blocked or product-gap item records the decision
  source or missing evidence
- **AND** OpenSpec specs remain the authority when they conflict with the older
  design baseline

#### Scenario: Held retrieval strategies do not enter by inertia

- **WHEN** lexical/RRF, Qwen sparse retrieval, graph defaults or candidate
  tuning defaults are considered for v1.0
- **THEN** they remain out of scope unless a current OpenSpec change provides
  evidence that satisfies the retrieval-quality and graph-store gates
- **AND** retrieval follows the current default product path defined by
  retrieval-quality

#### Scenario: Core readiness does not authorize final release

- **WHEN** M21 release package, offline demo and quality gate evidence exist
- **THEN** the system treats that evidence as pre-v1 core readiness
- **AND** no manual v1.0 tag or final release should be cut until
  `v1-product-completion` is satisfied

### Requirement: Readiness audit separates core completion from release package

The system MUST measure v1.0 readiness as a product-completion checklist, not
only as a release package checklist.

#### Scenario: Readiness status uses product categories

- **WHEN** the readiness audit is updated
- **THEN** each item is marked `done`, `core_ready`, `product_gap`,
  `deferred` or `blocked`
- **AND** the audit separates product core, authoring, ingestion operations,
  onboarding, docs, demo evidence and validation gates
- **AND** the percentage estimate is derived from that product-completion
  checklist

#### Scenario: Final PR sequence stays small

- **WHEN** readiness work is planned
- **THEN** it is split into small PRs for product authoring, ingestion
  operations, onboarding/demo and release quality gate
- **AND** unrelated runtime feature work is not mixed into the planning PR

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
