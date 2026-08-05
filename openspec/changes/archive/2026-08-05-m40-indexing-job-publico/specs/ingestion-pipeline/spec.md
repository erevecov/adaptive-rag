## ADDED Requirements

### Requirement: Successful ingest enqueues public indexing job

The system MUST enqueue a follow-up `index_document_version` job when an
`ingest_source` job completes successfully, so chunking and embeddings run on
the public worker path rather than only inside privileged smokes.

#### Scenario: Ingest success enqueues indexing without creating chunks yet

- **WHEN** a worker completes an `ingest_source` job successfully
- **THEN** a new job with `job_type = index_document_version` is created in the
  same project
- **AND** the payload includes the resulting `document_version_id` and
  `source_id`
- **AND** the indexing job starts with `status = queued`
- **AND** the completed ingest alone still does not create chunks or embeddings

#### Scenario: Idempotent re-ingest still enqueues indexing

- **WHEN** an `ingest_source` job reuses an existing document version
- **THEN** the system still enqueues an `index_document_version` job for that
  version
- **AND** indexing pipelines remain free to reuse existing chunks/embeddings

### Requirement: Public indexing job builds searchable corpus

The system MUST process `index_document_version` jobs by running chunking,
contextualization, dense embeddings and sparse embeddings for the target
document version inside the project.

#### Scenario: Index job produces chunks and embeddings

- **WHEN** a worker processes a queued `index_document_version` job for a
  document version in the same project
- **THEN** the system creates or reuses chunks for that version
- **AND** generates or reuses contextual summaries for those chunks
- **AND** writes dense and sparse embeddings for those chunks
- **AND** marks the indexing job as `succeeded`
- **AND** records lease/complete job events

#### Scenario: Missing document version blocks indexing job

- **WHEN** an `index_document_version` job references a document version outside
  the job project
- **THEN** the job is marked `blocked`
- **AND** no chunks or embeddings are written for foreign projects

## MODIFIED Requirements

### Requirement: Ingestion pipeline no implementa chunking ni embeddings

El sistema MUST mantener el procesamiento de `ingest_source` limitado a parsing
y persistencia de `document_versions`. El indexing (chunks/embeddings) MUST
ocurrir solo via jobs `index_document_version` u operaciones de index explicitas
equivalentes, no como efecto colateral silencioso de `ingest_source`.

#### Scenario: Pipeline de ingest no crea chunks

- **WHEN** un job `ingest_source` termina exitosamente
- **THEN** no se crean chunks en ese mismo job
- **AND** no se llaman providers de embeddings en ese mismo job
- **AND** el sistema encola el trabajo de indexing por separado
