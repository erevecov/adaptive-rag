# llm-judge Specification

## Purpose

Optional LLM-as-judge metrics for chat eval cases under an explicit budget.

## Requirements

### Requirement: Judge is opt-in and budgeted

The system MUST keep LLM-as-judge disabled by default and MUST require
`--max-cost-usd` greater than zero when judge mode is enabled.

#### Scenario: Judge without budget fails closed

- **WHEN** a user enables `--llm-judge` without a positive `--max-cost-usd`
- **THEN** the command fails with a stable configuration error
- **AND** no judge calls are made

### Requirement: Offline judge is deterministic and offline-safe

#### Scenario: Offline judge adds metrics without network

- **WHEN** evals run offline with `--llm-judge` and a valid budget
- **THEN** chat cases receive faithfulness and response_relevancy metrics
- **AND** no hosted provider is required for the fake judge path

### Requirement: Judge metrics are informational by default

#### Scenario: Suite status ignores judge scores

- **WHEN** judge metrics are attached to a report
- **THEN** suite pass/fail continues to use existing retrieval/chat thresholds
- **AND** aggregate means appear on the report metrics map
