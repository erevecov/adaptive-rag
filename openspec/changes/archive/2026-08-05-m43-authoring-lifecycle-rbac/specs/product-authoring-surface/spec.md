## ADDED Requirements

### Requirement: Projects can be updated and soft-deleted

The system MUST allow authorized clients to rename projects and soft-delete them
so removed projects leave the default list while remaining auditable.

#### Scenario: Admin renames project

- **WHEN** a project admin PATCHes a project name
- **THEN** the project name is updated

#### Scenario: Superadmin soft-deletes project

- **WHEN** a superadmin DELETEs a project
- **THEN** the project gains `deleted_at`
- **AND** subsequent GET/list omit it

### Requirement: Sources can be updated and soft-deleted with index cascade

The system MUST allow authorized clients to update source metadata and soft-delete
sources, cascading removal of searchable index rows for that source.

#### Scenario: Contributor updates source metadata

- **WHEN** a contributor PATCHes source tags or content metadata
- **THEN** the source is updated

#### Scenario: Admin soft-deletes source and cascades index

- **WHEN** a project admin DELETEs a source
- **THEN** the source is soft-deleted
- **AND** documents/chunks/embeddings for that source are removed
