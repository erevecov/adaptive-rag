## ADDED Requirements

### Requirement: Strategy gate decisions preserve dense default until proven

The system MUST preserve `dense` as default unless the retrieval strategy gate
reports a non-dense strategy that improves quality without regressions.

#### Scenario: Gate keeps equal strategies opt-in

- **WHEN** lexical, hybrid RRF, dense_sparse or rerank match dense hit rate
- **AND** they introduce no case regressions, citation loss or metadata filter
  failures
- **THEN** the gate assigns `keep_opt_in`
- **AND** `recommended_default` remains `dense`

#### Scenario: Gate blocks unsafe strategies

- **WHEN** a strategy fails the suite, regresses a case, loses citation coverage
  or violates metadata filter behavior
- **THEN** the gate assigns `no_go`
- **AND** the overall gate status is `failed`

#### Scenario: Gate holds graph without operational evidence

- **WHEN** graph retrieval passes offline quality comparison
- **THEN** the gate assigns `hold`
- **AND** graph is not recommended as default without separate live operational
  evidence
