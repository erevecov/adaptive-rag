# chat-frontend Specification Delta

## ADDED Requirements

### Requirement: Frontend onboarding points to seeded chat data

The frontend documentation MUST help users create cited local data before using
the chat workspace.

#### Scenario: User prepares data before opening chat UI

- **WHEN** a user follows the first-run runbook
- **THEN** the docs explain how to create a project with cited data using
  `adaptive-rag first-run smoke`
- **AND** the resulting project id can be reused in the chat UI
