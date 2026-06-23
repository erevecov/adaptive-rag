## ADDED Requirements

### Requirement: Audit trail stores lexical and RRF scores when present

The chat audit trail MUST preserve retrieval score metadata for non-dense
strategies without changing the default chat retrieval strategy.

#### Scenario: Retrieved chunks store strategy scores

- **WHEN** serialized retrieval results include dense, lexical or RRF score
  metadata
- **THEN** durable retrieved chunk rows store those values in the existing score
  columns
- **AND** missing score metadata remains nullable for legacy dense results
