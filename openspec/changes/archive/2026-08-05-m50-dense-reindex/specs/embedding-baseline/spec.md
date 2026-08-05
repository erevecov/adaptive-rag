## ADDED Requirements

### Requirement: Dense reindex walks project document versions

The system MUST provide a dense reindex operation that embeds all document
versions for a project (or a single version) and emits a JSON report with
counts and a watermark timestamp.

#### Scenario: Project dense reindex reports watermark

- **WHEN** dense reindex runs for a project with chunked versions
- **THEN** it returns embedded and reused counts
- **AND** includes started_at, finished_at and watermark fields

#### Scenario: Force reindex recomputes existing embeddings

- **WHEN** dense reindex runs with force for versions that already have embeddings
- **THEN** chunks are re-embedded rather than only reused
