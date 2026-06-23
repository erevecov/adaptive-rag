# Delta for v1-product-completion

## ADDED Requirements

### Requirement: V1 represents a finished local-first product

The system MUST define v1 as a complete single-user local-first product, not as
a portfolio-only release of the current core.

#### Scenario: V1 cannot be tagged from core readiness alone

- **WHEN** M21 release readiness evidence exists
- **THEN** it is treated as pre-v1 core readiness evidence
- **AND** it does not authorize a manual v1.0 tag or final release by itself
- **AND** v1.0 remains blocked until the product-completion requirements are
  satisfied

#### Scenario: Product completion uses user-owned data

- **WHEN** v1 product readiness is evaluated
- **THEN** the happy path starts from a user-created project and user-provided
  sources
- **AND** the user can ingest those sources without editing database rows or
  relying on hidden fixtures
- **AND** the user can query the resulting corpus through public chat or
  retrieval surfaces

### Requirement: V1 provides public authoring and ingestion operations

The system MUST expose the minimum public operations needed to create projects,
create sources, run ingestion and inspect job state.

#### Scenario: User creates a project and source

- **WHEN** a user starts from an empty local installation
- **THEN** the product exposes a documented public path to create a project
- **AND** exposes a documented public path to add at least Markdown, TXT or URL
  sources to that project
- **AND** the path does not require importing private fixtures or direct SQL

#### Scenario: User monitors ingestion state

- **WHEN** ingestion is requested for a project source
- **THEN** the product exposes job status, failure reason and retry/dead-letter
  state through public surfaces
- **AND** errors are actionable without reading internal logs as the primary
  interface

### Requirement: V1 onboarding is reproducible without internal fixtures

The system MUST provide a first-run path that a reviewer or user can execute
locally with documented inputs and expected outputs.

#### Scenario: First run setup reaches usable chat

- **WHEN** a user follows the v1 runbook on a clean local environment
- **THEN** the user can start required services, apply migrations, create a
  project, add a source, ingest it and ask a cited question
- **AND** optional hosted providers and graph services are clearly marked
  opt-in and are not required for the default path

#### Scenario: Final demo proves product flow

- **WHEN** the final v1 demo is run
- **THEN** it produces evidence from user-owned or public sample inputs created
  through the documented surfaces
- **AND** it reports retrieval/chat success, citations, job state and basic
  observability

### Requirement: V1 backlog excludes aspirational features by default

The system MUST keep aspirational or high-blast-radius features outside v1
unless a future OpenSpec change proves they are required for product
completion.

#### Scenario: Experimental retrieval remains gated

- **WHEN** lexical/RRF, Qwen sparse retrieval, graph retrieval defaults or
  candidate tuning defaults are proposed for v1
- **THEN** they remain out of the default product-completion gate unless a
  current OpenSpec change provides evidence that satisfies the relevant
  quality gates

#### Scenario: Advanced product surfaces remain explicit deferrals

- **WHEN** auth multi-user, PDF/Office ingestion, voice, MCP server, hosted
  observability or advanced admin workflows are proposed for v1
- **THEN** the change must state whether they are required for a finished
  local-first single-user product or remain deferred
- **AND** they do not enter v1 by inertia
