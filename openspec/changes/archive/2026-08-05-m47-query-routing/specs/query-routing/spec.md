## ADDED Requirements

### Requirement: Rule-based query router selects retrieval routes

The system MUST classify chat queries with a deterministic rule-based router
into `skip_retrieval`, `dense_sparse`, or `graph` without requiring a hosted
LLM by default.

#### Scenario: Greeting skips retrieval

- **WHEN** the query is a short greeting or thanks phrase
- **THEN** the router selects `skip_retrieval`

#### Scenario: Default falls back to dense_sparse

- **WHEN** the query is a factual content question without graph cues
- **THEN** the router selects `dense_sparse`

#### Scenario: Graph pattern with graph ready selects graph

- **WHEN** the query matches relationship/entity patterns
- **AND** graph is ready
- **THEN** the router selects `graph`

#### Scenario: Graph pattern without graph ready falls back

- **WHEN** the query matches graph patterns
- **AND** graph is not ready
- **THEN** the router selects `dense_sparse`

### Requirement: eval_routing measures router correctness

The system MUST provide a CI-safe `eval_routing` suite that scores the router
against labeled cases without live providers.

#### Scenario: Default suite passes for rule router

- **WHEN** `eval_routing` runs against the default labeled cases
- **THEN** all cases pass for the rule-based router
