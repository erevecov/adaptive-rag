## ADDED Requirements

### Requirement: Retrieval surface exposes lexical and hybrid RRF strategies

The system MUST expose local lexical retrieval and hybrid dense+lexical RRF as
explicit retrieval strategies without changing the dense default.

#### Scenario: Lexical strategy returns original citations

- **WHEN** retrieval is requested with `strategy=lexical`
- **THEN** the system ranks chunks by lexical match against contextualized
  lexical input
- **AND** returns result payloads with `strategy` equal to `lexical`
- **AND** citation snippets are sourced from original normalized document text

#### Scenario: Hybrid RRF fuses dense and lexical candidates

- **WHEN** retrieval is requested with `strategy=hybrid_rrf`
- **THEN** the system runs dense and lexical candidate lists after applying
  project and metadata filters
- **AND** fuses candidate ranks with reciprocal rank fusion
- **AND** emits at most one result per chunk with stable ordering

#### Scenario: Dense remains default

- **WHEN** no retrieval strategy is supplied by API, CLI, chat or eval callers
- **THEN** the system uses `dense`
- **AND** lexical and hybrid RRF never run implicitly

#### Scenario: Result metadata preserves strategy scores

- **WHEN** lexical or hybrid RRF returns results
- **THEN** result payloads include score metadata for the active strategy
- **AND** existing rerank metadata remains available when rerank is explicitly
  requested
