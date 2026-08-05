## MODIFIED Requirements

### Requirement: First-run smoke reaches cited chat

The system MUST provide a local first-run command that starts from public
product inputs and reaches a cited chat answer without hidden fixtures or
hosted credentials, using the same public ingestion and indexing job path as
API/CLI workers.

#### Scenario: User runs first-run smoke with default sample content

- **WHEN** a user runs `adaptive-rag first-run smoke` against an initialized
  local database
- **THEN** the command creates a project and Markdown source through public
  authoring services
- **AND** enqueues and processes an `ingest_source` job through the public
  worker path
- **AND** processes the follow-up `index_document_version` job through the same
  worker path (chunk → contextualize → dense/sparse embed)
- **AND** does not call privileged inline indexing pipelines outside that job
  path
- **AND** asks a chat question and returns at least one citation
- **AND** emits a JSON report with ids, job status, chunk/embed counts, answer
  and citation count

#### Scenario: User supplies own content and question

- **WHEN** a user runs first-run smoke with `--content` and `--question`
- **THEN** the created source uses that content
- **AND** the chat question uses the supplied question
- **AND** the report remains machine-readable JSON

### Requirement: First-run reports contextualized indexing

The system MUST expose generated Contextual Retrieval evidence in the local
first-run report, produced by the public indexing job path.

#### Scenario: First-run contextualizes before embedding

- **WHEN** a user runs `adaptive-rag first-run smoke`
- **THEN** the indexing job generates contextual summaries after chunking and
  before dense embedding
- **AND** the JSON report includes `contextualized_chunk_count` and
  `reused_contextualized_chunk_count`
- **AND** the contextualized plus reused count covers every reported chunk

#### Scenario: First-run citations remain original text

- **WHEN** chat returns citations for the first-run answer
- **THEN** citation snippets are sourced from the original normalized document
  text
- **AND** generated contextual summaries do not become citation snippets
