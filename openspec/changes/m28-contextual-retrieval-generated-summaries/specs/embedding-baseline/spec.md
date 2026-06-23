## ADDED Requirements

### Requirement: Contextual summaries are generated before embedding

The system MUST provide a project-scoped contextualization pipeline that fills
`chunks.contextual_summary` before dense embeddings are generated.

#### Scenario: Pipeline fills missing summaries

- **WHEN** a document version has chunks without `contextual_summary`
- **THEN** the contextualization pipeline generates one bounded summary per
  chunk
- **AND** persists it on `chunks.contextual_summary`
- **AND** preserves the original chunk offsets and normalized document text

#### Scenario: Pipeline reuses existing summaries

- **WHEN** a chunk already has a non-empty `contextual_summary`
- **THEN** the contextualization pipeline reuses it
- **AND** does not regenerate or overwrite the field

#### Scenario: Cross-project versions are rejected

- **WHEN** contextualization is requested with a `project_id` that does not own
  the document version
- **THEN** the system returns a stable error
- **AND** no chunks are updated

#### Scenario: Generated context drives embedding inputs

- **WHEN** dense embedding runs after contextualization
- **THEN** generated summaries are included in the embedding and lexical inputs
- **AND** embedding metadata records the contextualized input kind and hashes
