# Delta for v1-product-completion

## ADDED Requirements

### Requirement: V1 product completion includes ingestion operations

The product-completion gate MUST require public ingestion execution and job
state before v1.0 can be released.

#### Scenario: Product flow ingests authored sources

- **WHEN** M24 is complete
- **THEN** a user can enqueue ingestion for an authored source through public
  surfaces
- **AND** a user can process at least one ready ingestion job locally
- **AND** job status and failure reason are visible without direct SQL
