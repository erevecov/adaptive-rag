## ADDED Requirements

### Requirement: Post-v1 retrieval expansion remains opt-in until gated

The system MUST treat post-v1 contextual, lexical, sparse, graph and hybrid
retrieval capabilities as opt-in until a strategy gate proves promotion is
safe.

#### Scenario: Expansion track preserves dense default

- **WHEN** post-v1 retrieval capabilities are implemented
- **THEN** `dense` retrieval remains the default path
- **AND** each new retrieval capability requires explicit API, CLI or eval
  selection
- **AND** dense remains the fallback when an opt-in branch cannot run

#### Scenario: Frontend polish follows stable retrieval contracts

- **WHEN** frontend polish is planned after v1
- **THEN** contextual retrieval, lexical/RRF and sparse retrieval must first
  expose stable backend contracts or be explicitly excluded from the polish
  scope
- **AND** the frontend must not invent modes that lack API/CLI/eval contracts

### Requirement: Advanced retrieval sequence is staged by risk

The system MUST implement advanced retrieval in a risk-ordered sequence before
comparing promotion decisions.

#### Scenario: Contextual retrieval precedes new candidate branches

- **WHEN** the post-v1 retrieval expansion begins
- **THEN** generated Contextual Retrieval is the first implementation milestone
- **AND** it reuses existing chunk context fields and embedding input contracts
- **AND** it measures dense retrieval with and without generated context

#### Scenario: Lexical and RRF precede sparse retrieval

- **WHEN** contextual retrieval has a stable contract
- **THEN** local lexical retrieval and RRF are implemented before Qwen sparse
- **AND** lexical retrieval preserves project isolation, metadata filters,
  stable ordering and original citations
- **AND** RRF only fuses candidate lists that already satisfy those constraints

#### Scenario: Sparse retrieval verifies provider docs before coding

- **WHEN** Qwen sparse or `dense_sparse` retrieval is implemented
- **THEN** the change verifies current provider documentation before defining
  request payloads, response parsing, storage, scoring or cost assumptions
- **AND** sparse retrieval remains opt-in until the strategy gate reports a
  promotion decision

### Requirement: Retrieval strategy gate decides promotion

The system MUST compare advanced retrieval modes before changing defaults or
frontend assumptions.

#### Scenario: Strategy gate compares all ready modes

- **WHEN** contextual, lexical/RRF and sparse retrieval are ready enough to
  evaluate
- **THEN** the gate compares dense, contextual dense, lexical, sparse, hybrid
  RRF, graph opt-in and rerank where available
- **AND** it reports quality, regressions, latency, cost, fallback, filter
  behavior and citation coverage
- **AND** it assigns each strategy a decision of `promote`, `keep_opt_in`,
  `hold`, `no_go` or `needs_more_data`
