# retrieval-playground Specification

## Purpose

UI playground to run project retrieval and inspect ranked hits.

## Requirements

### Requirement: Operators can search without chat

#### Scenario: Submit query with strategy

- **WHEN** an operator enters a query for the selected project and searches
- **THEN** the client calls `POST /projects/{id}/retrieval/search`
- **AND** results show rank, score, strategy, source, and snippet
