## ADDED Requirements

### Requirement: Optional rerank fails open to bounded baseline retrieval

The system MUST preserve the already computed baseline retrieval when rerank
cannot complete for an operational reason, and MUST expose a stable secret-safe
fallback reason.

#### Scenario: Missing rerank configuration preserves baseline

- **WHEN** rerank is enabled but its optional provider cannot be configured
- **THEN** retrieval returns at most the requested final limit from the
  baseline candidates
- **AND** preserves their baseline order, fields, citations, strategy metadata,
  and prior fallback state
- **AND** each result reports `rerank_not_configured` and `used_rerank=false`

#### Scenario: Provider failure preserves baseline

- **WHEN** rerank raises a provider or rerank-result contract error
- **THEN** retrieval returns the bounded baseline order without repeating the
  baseline search
- **AND** each result reports `rerank_unavailable` and `used_rerank=false`

#### Scenario: Budget failure preserves baseline

- **WHEN** rerank is rejected or stopped by the provider budget guard
- **THEN** retrieval returns the bounded baseline order
- **AND** each result reports `rerank_budget_exceeded` and
  `used_rerank=false`

#### Scenario: Earlier fallback reason is preserved

- **WHEN** a baseline result already has a fallback reason before rerank fails
- **THEN** the existing top-level fallback reason remains unchanged
- **AND** the rerank reason is recorded in `rerank_metadata.fallback_reason`

#### Scenario: Unexpected rerank exception remains visible

- **WHEN** rerank raises an exception outside the known operational contracts
- **THEN** the request fails instead of silently degrading

#### Scenario: Rerank-disabled retrieval remains lazy

- **WHEN** retrieval does not enable rerank
- **THEN** no rerank provider is constructed or called
- **AND** no rerank fallback metadata is added

#### Scenario: Strict runtime and eval validation remains fail-closed

- **WHEN** direct runtime provider resolution or hosted rerank eval setup lacks
  required configuration
- **THEN** it returns the existing stable configuration error
- **AND** it does not silently measure baseline retrieval as rerank
