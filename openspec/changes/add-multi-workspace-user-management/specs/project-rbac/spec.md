## MODIFIED Requirements

### Requirement: Local users resolve the current actor

The system MUST resolve every protected API request to an active global user
through a human session cookie or a hash-only technical bearer token.

#### Scenario: Human login creates a server-side session

- **GIVEN** an active user with a valid local password
- **WHEN** the user authenticates with normalized email and password
- **THEN** the server creates a hash-only bounded session
- **AND** sets an HttpOnly, SameSite cookie
- **AND** plaintext credentials are not persisted or logged

#### Scenario: Browser mutation requires CSRF protection

- **GIVEN** a request authenticated by session cookie
- **WHEN** it mutates protected state
- **THEN** its Origin must be allowed
- **AND** its session-bound CSRF header must be valid

#### Scenario: Empty installation does not grant implicit authority

- **GIVEN** the user table is empty
- **WHEN** a protected endpoint is called without credentials
- **THEN** it returns an authentication error
- **AND** only setup with the configured bootstrap secret can create the first
  superadmin

### Requirement: Workspace memberships define independent workspace roles

The system MUST use one membership per user/workspace to grant `admin`,
`contributor` or `viewer`, independently across workspaces.

#### Scenario: Same user has different roles

- **GIVEN** a user is viewer in workspace A and admin in workspace B
- **WHEN** permissions are evaluated in each workspace
- **THEN** viewer permissions apply in A
- **AND** admin permissions apply in B
- **AND** neither membership mutates or authorizes the other

#### Scenario: Admin adds an existing identity by email

- **GIVEN** a workspace admin and an existing global user
- **WHEN** the admin adds the exact normalized email to that workspace
- **THEN** a membership with viewer, contributor or admin role is created
- **AND** no global identity attributes can be changed

## ADDED Requirements

### Requirement: Human credentials support one-time temporary passwords

The system MUST generate temporary passwords on user creation and admin reset,
show them only in the mutation response, and force a password change.

#### Scenario: Superadmin creates ordinary user

- **WHEN** a superadmin creates an ordinary user with an initial workspace role
- **THEN** identity, credential and membership commit atomically
- **AND** the response returns a generated temporary password once
- **AND** subsequent reads never return it

#### Scenario: Mandatory change revokes other sessions

- **GIVEN** a user authenticates with a temporary password
- **WHEN** the user replaces it
- **THEN** the mandatory-change flag is cleared
- **AND** all other sessions for the user are revoked

### Requirement: Last administrator authority is preserved

The system MUST reject mutations that remove the final active global or
workspace administrator, including concurrent requests.

#### Scenario: Last superadmin cannot lose authority

- **GIVEN** exactly one active superadmin remains
- **WHEN** that identity is suspended or demoted
- **THEN** the transaction fails with `last_active_superadmin`
- **AND** the identity remains an active superadmin

#### Scenario: Last active workspace admin cannot leave admin role

- **GIVEN** exactly one active admin remains in a workspace with active members
- **WHEN** its membership is removed or demoted
- **THEN** the transaction fails with `last_active_workspace_admin`
- **AND** the membership remains admin

### Requirement: Suspension preserves membership configuration

The system MUST suspend identities reversibly while terminating their human
sessions and retaining workspace memberships.

#### Scenario: Suspended user loses access but keeps memberships

- **WHEN** a superadmin suspends a user
- **THEN** all human sessions are revoked
- **AND** human sessions and technical bearer tokens stop authenticating
- **AND** workspace membership rows remain for later reactivation
