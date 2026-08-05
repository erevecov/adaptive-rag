## ADDED Requirements

### Requirement: V1 quality gate uses public indexing jobs

The default v1 product quality gate MUST index evidence through the public
ingestion/indexing job path used by workers, not via privileged inline
indexing-only orchestration.

#### Scenario: Quality gate drains public jobs before cited chat

- **WHEN** a reviewer runs `adaptive-rag v1 quality-gate` with fake providers
- **THEN** the gate creates source work via public authoring
- **AND** processes `ingest_source` and `index_document_version` via the shared
  worker entry points
- **AND** only then runs cited chat against the indexed corpus
- **AND** reports chunk/contextual/embed evidence produced by that path
