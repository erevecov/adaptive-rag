## ADDED Requirements

### Requirement: Provider runtime supports sparse embeddings opt-in

The system MUST expose sparse embedding providers without changing the default
fake provider runtime or dense embedding contract.

#### Scenario: Qwen sparse embeddings use DashScope sparse output

- **WHEN** a live sparse provider is configured for Qwen
- **THEN** it requests DashScope text embeddings with `output_type=sparse`
- **AND** uses `text_type=document` for stored chunks
- **AND** uses `text_type=query` for retrieval queries
- **AND** parses each sparse item as `index`, `value` and optional `token`

#### Scenario: Sparse provider records usage as embedding

- **WHEN** a sparse embedding provider call completes, fails or is blocked
- **THEN** provider usage uses operation `embedding`
- **AND** does not introduce a new provider usage operation value
- **AND** does not log or persist API keys

#### Scenario: Fake sparse provider is deterministic

- **WHEN** tests or offline evals request sparse embeddings without live mode
- **THEN** the fake sparse provider returns deterministic sparse vectors
- **AND** no network call is made
