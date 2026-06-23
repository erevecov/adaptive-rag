## ADDED Requirements

### Requirement: Lexical and RRF preserve retrieval safety invariants

The system MUST keep project isolation, metadata filters, stable ordering and
original citations across lexical and hybrid RRF retrieval.

#### Scenario: Lexical filters before ranking

- **WHEN** lexical retrieval receives a metadata filter
- **THEN** it applies `project_id` and metadata filters before ranking
- **AND** excludes chunks outside the project or filter scope

#### Scenario: RRF deduplicates candidates

- **WHEN** a chunk appears in both dense and lexical candidate lists
- **THEN** hybrid RRF emits the chunk once
- **AND** records the dense rank, lexical rank and RRF score in result metadata

#### Scenario: Rerank remains explicit

- **WHEN** lexical or hybrid RRF is requested without rerank options
- **THEN** no rerank provider is required or called
- **AND** rerank can still be applied only when explicit rerank options are
  supplied
