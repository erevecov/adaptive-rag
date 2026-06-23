## ADDED Requirements

### Requirement: Offline evals can select dense_sparse retrieval

The eval runner MUST allow retrieval suites to run with `strategy=dense_sparse`
without making hosted calls by default.

#### Scenario: Eval CLI selects dense_sparse retrieval

- **WHEN** `adaptive-rag evals run` receives
  `--retrieval-strategy dense_sparse` in offline mode
- **THEN** retrieval eval cases run with `strategy=dense_sparse`
- **AND** the default remains `dense` when no strategy flag is supplied
