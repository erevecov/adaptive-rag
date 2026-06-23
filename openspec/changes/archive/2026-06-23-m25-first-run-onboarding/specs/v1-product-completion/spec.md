# v1-product-completion Specification Delta

## ADDED Requirements

### Requirement: V1 product completion includes first-run onboarding

The product-completion gate MUST require a reproducible first-run path before
v1.0 can be released.

#### Scenario: First-run path proves the product flow

- **WHEN** M25 is complete
- **THEN** a user can follow documented local setup from an empty database
- **AND** run a public first-run smoke command
- **AND** receive evidence for project/source creation, ingestion job status,
  chunking, embeddings, cited chat and next commands
