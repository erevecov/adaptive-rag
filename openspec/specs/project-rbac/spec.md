# project-rbac Specification

## Purpose
Define local first-party users, global superadmin authority, project-scoped
memberships, and role gates for project discovery, chat, retrieval, authoring,
ingestion, runtime overrides, and knowledge proposal workflows.
## Requirements
### Requirement: Local users resolve the current actor

The system MUST resolve every protected API request to an active local user
before applying project permissions.

#### Scenario: Request without actor is rejected

- **WHEN** a protected endpoint is called without a valid local bearer token or
  equivalent current-user credential
- **THEN** the request fails with a stable authentication error
- **AND** no project, chat or knowledge data is returned

#### Scenario: Inactive user cannot act

- **GIVEN** a local user exists with `is_active = false`
- **WHEN** that user's credential is used
- **THEN** protected endpoints reject the request with `inactive_user`

#### Scenario: Token storage does not persist plaintext

- **WHEN** a local access token is issued
- **THEN** the stored row contains a non-reversible token hash
- **AND** API responses never include the token value after issuance

### Requirement: Superadmin is a system role

The system MUST model `superadmin` as a global system role separate from
project membership roles.

#### Scenario: Superadmin can administer all projects

- **GIVEN** a user has `system_role = "superadmin"`
- **WHEN** they create, inspect or administer any project
- **THEN** the operation is allowed without requiring a project membership row

#### Scenario: Non-superadmin cannot create projects

- **GIVEN** an active user without `system_role = "superadmin"`
- **WHEN** they call project creation
- **THEN** the request fails with a stable system-role authorization error

#### Scenario: Project admin cannot create superadmin

- **GIVEN** a project `admin`
- **WHEN** they create or update a user through project member management
- **THEN** they cannot set `system_role = "superadmin"`
- **AND** the request fails without changing the target user's system role

### Requirement: Project memberships define project roles

The system MUST use project memberships to grant `admin`, `contributor` or
`viewer` access inside a project.

#### Scenario: Member has one effective project role

- **GIVEN** a user is assigned to a project
- **WHEN** their membership is read
- **THEN** the role is exactly one of `admin`, `contributor` or `viewer`
- **AND** duplicate active memberships for the same user/project are rejected

#### Scenario: Project admin manages members in their project

- **GIVEN** a user has project role `admin`
- **WHEN** they add or update a member in that same project
- **THEN** they may assign `viewer`, `contributor` or `admin`
- **AND** they cannot modify memberships in other projects

#### Scenario: Contributor cannot manage members

- **GIVEN** a user has project role `contributor`
- **WHEN** they call a project member management endpoint
- **THEN** the request fails with a stable project-role authorization error

### Requirement: Project discovery is broader than project access

The system MUST let authenticated users see project names while enforcing
membership before project data or tools are accessible.

#### Scenario: User lists all project names with access status

- **GIVEN** projects `A` and `B` exist
- **AND** the current user is a member only of project `A`
- **WHEN** they list projects
- **THEN** the response includes the names of `A` and `B`
- **AND** marks `A` as accessible
- **AND** marks `B` as locked or not accessible

#### Scenario: Locked project cannot be opened

- **GIVEN** a user is not a member of a project and is not superadmin
- **WHEN** they call a project-scoped chat, retrieval, source, ingestion,
  runtime override or observability route for that project
- **THEN** the request fails with a stable project-access error
- **AND** no project-private data is returned

### Requirement: Project roles gate tool surfaces

The system MUST enforce a consistent minimum role for each project-scoped
surface.

#### Scenario: Viewer can use chat and retrieval

- **GIVEN** a user has project role `viewer`
- **WHEN** they call chat or retrieval for that project
- **THEN** the request is allowed

#### Scenario: Viewer cannot author shared knowledge directly

- **GIVEN** a user has project role `viewer`
- **WHEN** they create a source directly or enqueue ingestion
- **THEN** the request fails
- **AND** they must use the knowledge proposal flow instead

#### Scenario: Contributor can manage knowledge

- **GIVEN** a user has project role `contributor`
- **WHEN** they create sources, enqueue ingestion or review knowledge
  proposals in that project
- **THEN** the request is allowed

#### Scenario: Project admin cannot delete or archive projects

- **GIVEN** a user has project role `admin`
- **WHEN** they attempt to archive or delete the project
- **THEN** the request fails unless they are also `superadmin`
