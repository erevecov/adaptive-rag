# first-run-onboarding Specification

## Purpose
TBD - created by archiving change m25-first-run-onboarding. Update Purpose after archive.
## Requirements
### Requirement: First-run smoke reaches cited chat

The system MUST provide a local first-run command that starts from public
product inputs and reaches a cited chat answer without hidden fixtures or
hosted credentials.

#### Scenario: User runs first-run smoke with default sample content

- **WHEN** a user runs `adaptive-rag first-run smoke` against an initialized
  local database
- **THEN** the command creates a project and Markdown source through public
  authoring services
- **AND** enqueues and processes an `ingest_source` job
- **AND** chunks and embeds the resulting document version with the default fake
  provider path
- **AND** asks a chat question and returns at least one citation
- **AND** emits a JSON report with ids, job status, chunk/embed counts, answer
  and citation count

#### Scenario: User supplies own content and question

- **WHEN** a user runs first-run smoke with `--content` and `--question`
- **THEN** the created source uses that content
- **AND** the chat question uses the supplied question
- **AND** the report remains machine-readable JSON

### Requirement: First-run failures are actionable

The first-run command MUST fail fast with stable messages when the default path
cannot reach usable chat.

#### Scenario: Ingestion blocks

- **WHEN** the ingestion job returns `blocked`
- **THEN** the command exits non-zero
- **AND** stderr includes the job error message

#### Scenario: Chat has no citations

- **WHEN** the first-run chat response has zero citations
- **THEN** the command exits non-zero
- **AND** stderr says `first-run chat returned no citations`

### Requirement: First-run runbook documents the local default

The system MUST document a clean local first run using fake providers and public
commands.

#### Scenario: User follows the runbook

- **WHEN** a user opens the first-run documentation
- **THEN** it lists dependency setup, database startup, Alembic migrations and
  `adaptive-rag first-run smoke`
- **AND** it marks hosted providers and graph services as opt-in
- **AND** it shows expected evidence fields from the JSON report
