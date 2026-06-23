## ADDED Requirements

### Requirement: First-run reports contextualized indexing

The system MUST expose generated Contextual Retrieval evidence in the local
first-run report before frontend polish depends on advanced retrieval modes.

#### Scenario: First-run contextualizes before embedding

- **WHEN** a user runs `adaptive-rag first-run smoke`
- **THEN** the command generates contextual summaries after chunking and before
  dense embedding
- **AND** the JSON report includes `contextualized_chunk_count` and
  `reused_contextualized_chunk_count`
- **AND** the contextualized plus reused count covers every reported chunk

#### Scenario: First-run citations remain original text

- **WHEN** chat returns citations for the first-run answer
- **THEN** citation snippets are sourced from the original normalized document
  text
- **AND** generated contextual summaries do not become citation snippets
