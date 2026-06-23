## ADDED Requirements

### Requirement: Offline retrieval evals can select advanced strategies

The offline eval runner MUST allow callers to run retrieval cases against
explicit retrieval strategies.

#### Scenario: Eval CLI selects lexical retrieval

- **WHEN** `adaptive-rag evals run` receives `--retrieval-strategy lexical`
- **THEN** retrieval eval cases run with `strategy=lexical`
- **AND** chat eval cases remain on the default chat retrieval path

#### Scenario: Eval CLI selects hybrid RRF retrieval

- **WHEN** `adaptive-rag evals run` receives `--retrieval-strategy hybrid_rrf`
- **THEN** retrieval eval cases run with `strategy=hybrid_rrf`
- **AND** the aggregate retrieval metrics keep the existing schema
