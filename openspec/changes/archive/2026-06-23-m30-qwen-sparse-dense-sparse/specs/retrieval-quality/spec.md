## ADDED Requirements

### Requirement: Sparse retrieval preserves retrieval invariants

Sparse retrieval and dense_sparse fusion MUST preserve project isolation,
metadata filters and original citations.

#### Scenario: Sparse retrieval applies filters before scoring

- **WHEN** sparse retrieval is requested with source/document/tag/date filters
- **THEN** candidates outside those filters are excluded before ranking
- **AND** results never cross project boundaries

#### Scenario: Sparse citations use original chunk text

- **WHEN** sparse retrieval returns a result for a contextualized chunk
- **THEN** the citation snippet is sourced from the original normalized document
  text
- **AND** contextual summaries do not become citation snippets

#### Scenario: Sparse rows are reproducible

- **WHEN** sparse backfill stores a row
- **THEN** it records provider, model, input hash and index fingerprint metadata
- **AND** rerunning with the same inputs reuses the row instead of duplicating it
