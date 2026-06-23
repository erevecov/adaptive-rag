# Delta for v1-product-completion

## ADDED Requirements

### Requirement: V1 product completion includes authoring surfaces

The product-completion gate MUST require public project and source authoring
before v1.0 can be released.

#### Scenario: Product flow starts without SQL

- **WHEN** v1 product readiness is evaluated
- **THEN** the user can create a project through a documented public surface
- **AND** the user can add at least Markdown, TXT and URL sources through a
  documented public surface
- **AND** the flow does not require direct SQL, private fixtures or test helpers

#### Scenario: Authoring precedes ingestion operations

- **WHEN** M23 is complete
- **THEN** projects and sources can be authored publicly
- **AND** ingestion execution and job-state operations remain explicit follow-up
  work for M24
