# v1-product-completion Specification

## Purpose
Definir el contrato de producto terminado para v1: una experiencia
local-first single-user que permite crear proyectos, agregar sources, ingerir
datos propios, consultar con citations y operar estado/errores sin depender de
fixtures internas ni SQL manual.
## Requirements
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

### Requirement: V1 product completion includes authoring surfaces

The product-completion gate MUST require public project and source authoring
before v1.0 can be released.

#### Scenario: Product flow starts without SQL

- **WHEN** v1 product readiness is evaluated
- **THEN** the user can create a project through a documented public surface
- **AND** the user can add at least Markdown, TXT and URL sources through a
  documented public surface
- **AND** the flow does not require direct SQL, private fixtures or test helpers

#### Scenario: Authoring precedes ingestion operations

- **WHEN** M23 is complete
- **THEN** projects and sources can be authored publicly
- **AND** ingestion execution and job-state operations remain explicit follow-up
  work for M24

### Requirement: V1 product completion includes ingestion operations

The product-completion gate MUST require public ingestion execution and job
state before v1.0 can be released.

#### Scenario: Product flow ingests authored sources

- **WHEN** M24 is complete
- **THEN** a user can enqueue ingestion for an authored source through public
  surfaces
- **AND** a user can process at least one ready ingestion job locally
- **AND** job status and failure reason are visible without direct SQL

### Requirement: V1 product completion includes first-run onboarding

The product-completion gate MUST require a reproducible first-run path before
v1.0 can be released.

#### Scenario: First-run path proves the product flow

- **WHEN** M25 is complete
- **THEN** a user can follow documented local setup from an empty database
- **AND** run a public first-run smoke command
- **AND** receive evidence for project/source creation, ingestion job status,
  chunking, embeddings, cited chat and next commands

### Requirement: V1 product completion includes final quality gate

The product-completion gate MUST include a final public command that produces
release evidence from the complete local-first product flow.

#### Scenario: Quality gate proves final product flow

- **WHEN** a reviewer runs `adaptive-rag v1 quality-gate` against an initialized
  local database
- **THEN** the command creates user/sample data through public product services
- **AND** it runs ingestion, chunking, embeddings and cited chat through the
  default local path
- **AND** it emits a machine-readable report with release criteria, first-run
  evidence, job state, indexing counts, citation count and release decision

#### Scenario: Quality gate keeps optional systems out of default release

- **WHEN** the v1 quality gate reports release evidence
- **THEN** hosted Qwen, hosted rerank and Neo4j remain marked opt-in
- **AND** auth multi-user, PDF/Office, voice, MCP server and hosted
  observability remain explicit deferrals
- **AND** retrieval uses the current default local path for v1.0 validation

### Requirement: Product completion includes post-runtime-settings acceptance

El producto MUST validar que runtime settings persistidos funcionan con el flujo
local completo despues de agregar provider connections, catalogo de modelos y
overrides por proyecto.

#### Scenario: Runtime acceptance complements v1 quality gate

- **WHEN** se evalua el producto despues de M34
- **THEN** el gate de acceptance ejecuta authoring, ingestion, indexing y chat
  citado con providers resueltos desde runtime settings persistidos
- **AND** conserva `adaptive-rag v1 quality-gate` como evidencia de release
  local-first
- **AND** no convierte Qwen hosted, providers locales ni graph en defaults

#### Scenario: Acceptance output is machine-readable

- **WHEN** el smoke termina correctamente
- **THEN** emite JSON con estado, criterios, evidencia de runtime settings,
  evidencia de first-run y sistemas opt-in diferidos
- **AND** cada criterio queda marcado como `passed`
