# Delta for repositories

## ADDED Requirements

### Requirement: Repositories support public authoring adapters

Repositories MUST expose the deterministic reads and writes required by public
API and CLI authoring surfaces while keeping transaction control with the caller.

#### Scenario: ProjectRepository lists projects without committing

- **WHEN** API or CLI lists projects
- **THEN** `ProjectRepository` returns projects in deterministic order
- **AND** the repository does not create, commit or rollback a transaction

#### Scenario: SourceRepository detects duplicate identity

- **WHEN** API or CLI creates a source
- **THEN** the authoring adapter can detect an existing source with the same
  `project_id`, `source_type` and `external_id`
- **AND** it can return a stable conflict before or after database constraint
  enforcement
