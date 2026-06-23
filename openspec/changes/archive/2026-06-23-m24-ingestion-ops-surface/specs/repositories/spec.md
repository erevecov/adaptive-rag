# Delta for repositories

## ADDED Requirements

### Requirement: Repositories support ingestion ops adapters

Repositories MUST expose enough project-scoped access for ingestion ops adapters
to avoid ad-hoc SQL in API and CLI layers.

#### Scenario: Job operations use caller-owned transactions

- **WHEN** ingestion ops list or requeue jobs through repositories
- **THEN** repository methods flush changes but do not commit or rollback
- **AND** API and CLI remain responsible for transaction boundaries
