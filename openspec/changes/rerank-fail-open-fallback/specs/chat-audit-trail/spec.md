## ADDED Requirements

### Requirement: Rerank fallback remains auditable

The system MUST distinguish successful rerank from rerank fallback in durable
chat audit data without requiring a schema migration.

#### Scenario: Fallback metadata does not imply successful rerank

- **WHEN** a retrieval result contains rerank metadata with
  `used_rerank=false`
- **THEN** the retrieval run stores `used_rerank=false`
- **AND** its retrieved chunks do not store a rerank score

#### Scenario: Rerank fallback reason is stored independently

- **WHEN** chat completes retrieval through a rerank fallback
- **THEN** the tool result summary stores `rerank_fallback_reason`
- **AND** a pre-existing top-level fallback reason remains unchanged

#### Scenario: Successful rerank audit remains compatible

- **WHEN** rerank succeeds and reports `used_rerank=true`
- **THEN** the retrieval run stores `used_rerank=true`
- **AND** existing rerank scores remain available on retrieved chunks
