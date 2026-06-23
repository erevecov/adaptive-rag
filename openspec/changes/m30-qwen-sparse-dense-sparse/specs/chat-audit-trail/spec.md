## ADDED Requirements

### Requirement: Audit trail stores sparse scores when present

The audit trail MUST preserve sparse retrieval score metadata without changing
the default chat retrieval strategy.

#### Scenario: Sparse retrieval scores are persisted

- **WHEN** serialized retrieval results include sparse score metadata
- **THEN** retrieved chunk audit rows store `sparse_score`
- **AND** continue storing dense, lexical, RRF and rerank scores when present
