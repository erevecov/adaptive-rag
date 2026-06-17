# Domain Schema Delta Spec

## ADDED Requirements

### Requirement: Project records define isolation and retrieval mode

The system SHALL persist project records that isolate all RAG data by `project_id` and define retrieval configuration.

#### Scenario: Project defaults to dense retrieval

- **WHEN** a project is created without an explicit embedding mode
- **THEN** the stored `embedding_mode` is `dense`
- **AND** `retrieval_contextualization_enabled` is `true`

#### Scenario: Project budget settings are persisted

- **WHEN** a project includes budget settings
- **THEN** the settings are stored in `budget_config_json`

### Requirement: Sources and documents preserve ingestion identity

The system SHALL persist sources and documents with stable identifiers, source type, external identifiers, metadata and project ownership.

#### Scenario: Documents belong to a project and source

- **WHEN** a document is created from a source
- **THEN** the document stores `project_id` and `source_id`
- **AND** repository queries can filter by either field

#### Scenario: Source metadata supports filtering

- **WHEN** a source has tags, source type or date metadata
- **THEN** those values are stored in typed columns or indexed metadata fields suitable for filtering

### Requirement: Document versions anchor normalized text and citations

The system SHALL store each parsed document version with normalized text, parser metadata, extraction metadata, content hash and index fingerprint.

#### Scenario: Chunk offsets refer to normalized text

- **WHEN** a chunk is created for a document version
- **THEN** `char_start` and `char_end` refer to offsets in `document_versions.normalized_text`

#### Scenario: Re-indexing preserves prior document versions

- **WHEN** a document is re-parsed with different normalized text or parser metadata
- **THEN** a new `document_versions` row is created
- **AND** existing chunks keep pointing to their original version

### Requirement: Chunks store dense embedding inputs and semantic boundaries

The system SHALL persist chunks with section metadata, token counts, neighbor links, chunker metadata, contextual retrieval reserved fields and dense embeddings.

#### Scenario: Dense embedding column has Qwen-compatible dimensions

- **WHEN** the schema is migrated
- **THEN** `chunks.embedding` is a pgvector column with 1024 dimensions

#### Scenario: Chunk lineage can be reconstructed

- **WHEN** chunks are retrieved for a document version
- **THEN** `ordinal`, `prev_chunk_id` and `next_chunk_id` allow the system to reconstruct local chunk order

### Requirement: Sparse embeddings are optional and isolated

The system SHALL store sparse embedding data in `chunk_sparse_embeddings` only when a project uses `dense_sparse` mode.

#### Scenario: Dense-only projects do not need sparse rows

- **WHEN** a project uses `embedding_mode = dense`
- **THEN** retrieval can operate without rows in `chunk_sparse_embeddings`

#### Scenario: Sparse rows preserve reproducibility metadata

- **WHEN** sparse embeddings are stored
- **THEN** each row includes sparse indices, sparse values, optional sparse tokens, sparse size, input hash and index fingerprint
