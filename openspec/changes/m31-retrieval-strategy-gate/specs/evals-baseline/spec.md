## ADDED Requirements

### Requirement: Offline evals expose a retrieval strategy gate

The eval surface MUST provide an offline command that compares ready retrieval
strategies against dense baseline without hosted calls by default.

#### Scenario: Strategy gate emits stable decisions

- **WHEN** `adaptive-rag evals strategy-gate <suite>` runs against a valid
  suite
- **THEN** it emits JSON with `dense_baseline`, `strategy_decisions`,
  `default_strategy` and `recommended_default`
- **AND** each decision row includes a strategy name, status, decision, reason,
  metrics and comparison metrics

#### Scenario: Contextual dense requires contextual evidence

- **WHEN** the strategy gate evaluates `contextual_dense`
- **AND** the suite evidence has no `contextual_summary` values
- **THEN** the row is skipped with decision `needs_more_data`
- **AND** the default recommendation remains `dense`

#### Scenario: Evals evidence can carry contextual summaries

- **WHEN** a suite declares `contextual_summary` on evidence
- **THEN** the loader accepts it as optional evidence metadata
- **AND** fixture projects can embed summary plus chunk text for
  `contextual_dense` comparisons
