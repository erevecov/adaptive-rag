## ADDED Requirements

### Requirement: Administration surfaces follow global and workspace scope

The frontend MUST separate global identities from workspace memberships and show
each surface only to authorized roles.

#### Scenario: Superadmin receives temporary password once

- **WHEN** user creation or reset succeeds
- **THEN** a modal shows the target email and temporary password
- **AND** offers an accessible copy action
- **AND** closing clears the secret from frontend state

#### Scenario: Workspace admin sees only workspace members

- **GIVEN** an ordinary workspace admin
- **WHEN** they open member administration
- **THEN** only members of the active workspace are listed
- **AND** they can add an existing user by exact email
- **AND** no global directory or global identity actions are exposed
