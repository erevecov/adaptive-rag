# workspace-rbac Specification

## Purpose
Define local first-party users, global superadmin authority, workspace-scoped
memberships, and role gates for workspace discovery, chat, retrieval, authoring,
ingestion, runtime overrides, and knowledge proposal workflows.
## Requirements
### Requirement: Local users resolve the current actor

The system MUST resolve every protected API request to an active local user
before applying workspace permissions.

#### Scenario: Request without actor is rejected

- **WHEN** a protected endpoint is called without a valid local bearer token or
  equivalent current-user credential
- **THEN** the request fails with a stable authentication error
- **AND** no workspace, chat or knowledge data is returned

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
workspace membership roles.

#### Scenario: Superadmin can administer all workspaces

- **GIVEN** a user has `system_role = "superadmin"`
- **WHEN** they create, inspect or administer any workspace
- **THEN** the operation is allowed without requiring a workspace membership row

#### Scenario: Non-superadmin cannot create workspaces

- **GIVEN** an active user without `system_role = "superadmin"`
- **WHEN** they call workspace creation
- **THEN** the request fails with a stable system-role authorization error

#### Scenario: Workspace admin cannot create superadmin

- **GIVEN** a workspace `admin`
- **WHEN** they create or update a user through workspace member management
- **THEN** they cannot set `system_role = "superadmin"`
- **AND** the request fails without changing the target user's system role

### Requirement: Workspace memberships define workspace roles

The system MUST use workspace memberships to grant `admin`, `contributor` or
`viewer` access inside a workspace.

#### Scenario: Member has one effective workspace role

- **GIVEN** a user is assigned to a workspace
- **WHEN** their membership is read
- **THEN** the role is exactly one of `admin`, `contributor` or `viewer`
- **AND** duplicate active memberships for the same user/workspace are rejected

#### Scenario: Workspace admin manages members in their workspace

- **GIVEN** a user has workspace role `admin`
- **WHEN** they add or update a member in that same workspace
- **THEN** they may assign `viewer`, `contributor` or `admin`
- **AND** they cannot modify memberships in other workspaces

#### Scenario: Contributor cannot manage members

- **GIVEN** a user has workspace role `contributor`
- **WHEN** they call a workspace member management endpoint
- **THEN** the request fails with a stable workspace-role authorization error

### Requirement: Workspace discovery is broader than workspace access

The system MUST let authenticated users see workspace names while enforcing
membership before workspace data or tools are accessible.

#### Scenario: User lists all workspace names with access status

- **GIVEN** workspaces `A` and `B` exist
- **AND** the current user is a member only of workspace `A`
- **WHEN** they list workspaces
- **THEN** the response includes the names of `A` and `B`
- **AND** marks `A` as accessible
- **AND** marks `B` as locked or not accessible

#### Scenario: Locked workspace cannot be opened

- **GIVEN** a user is not a member of a workspace and is not superadmin
- **WHEN** they call a workspace-scoped chat, retrieval, source, ingestion,
  runtime override or observability route for that workspace
- **THEN** the request fails with a stable workspace-access error
- **AND** no workspace-private data is returned

### Requirement: Workspace roles gate tool surfaces

The system MUST enforce a consistent minimum role for each workspace-scoped
surface.

#### Scenario: Viewer can use chat and retrieval

- **GIVEN** a user has workspace role `viewer`
- **WHEN** they call chat or retrieval for that workspace
- **THEN** the request is allowed

#### Scenario: Viewer cannot author shared knowledge directly

- **GIVEN** a user has workspace role `viewer`
- **WHEN** they create a source directly or enqueue ingestion
- **THEN** the request fails
- **AND** they must use the knowledge proposal flow instead

#### Scenario: Contributor can manage knowledge

- **GIVEN** a user has workspace role `contributor`
- **WHEN** they create sources, enqueue ingestion or review knowledge
  proposals in that workspace
- **THEN** the request is allowed

#### Scenario: Workspace admin cannot delete or archive workspaces

- **GIVEN** a user has workspace role `admin`
- **WHEN** they attempt to archive or delete the workspace
- **THEN** the request fails unless they are also `superadmin`

### Requirement: Membership delete and user/token lifecycle

The system MUST expose public operations to remove workspace memberships,
deactivate users, and revoke access tokens for local RBAC closeout.

#### Scenario: Admin removes membership

- **WHEN** a workspace admin DELETEs a membership
- **THEN** the membership is removed
- **AND** the user loses workspace access

#### Scenario: Superadmin deactivates user

- **WHEN** a superadmin deactivates a user
- **THEN** `is_active` is false
- **AND** the user cannot authenticate for new requests

#### Scenario: Superadmin revokes access token

- **WHEN** a superadmin revokes an access token
- **THEN** that token no longer authenticates

### Requirement: Role matrix denies unauthorized lifecycle ops

Lifecycle mutations MUST enforce role checks so viewers cannot mutate authoring
resources.

#### Scenario: Viewer cannot update or delete sources

- **WHEN** a viewer attempts PATCH or DELETE source
- **THEN** the API returns 403

