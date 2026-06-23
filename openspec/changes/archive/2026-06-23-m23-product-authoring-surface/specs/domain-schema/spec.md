# Delta for domain-schema

## ADDED Requirements

### Requirement: Current project and source schema supports public authoring

The existing project and source tables MUST be sufficient for M23 public
authoring unless implementation evidence proves a required product field is
missing.

#### Scenario: Project authoring uses existing project fields

- **WHEN** a project is created through the M23 public surface
- **THEN** it uses existing project fields such as `name`, `embedding_mode`,
  `retrieval_contextualization_enabled` and `budget_config_json`
- **AND** it does not require a migration for auth multi-user, slug or hosted
  settings

#### Scenario: Source authoring uses existing source fields

- **WHEN** a source is created through the M23 public surface
- **THEN** it uses existing source fields such as `project_id`, `source_type`,
  `external_id`, `tags` and `extra_metadata`
- **AND** inline text content for text-like sources is stored in
  `extra_metadata.content` for the current ingestion pipeline
