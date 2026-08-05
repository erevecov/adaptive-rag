## ADDED Requirements

### Requirement: Membership delete and user/token lifecycle

The system MUST expose public operations to remove project memberships,
deactivate users, and revoke access tokens for local RBAC closeout.

#### Scenario: Admin removes membership

- **WHEN** a project admin DELETEs a membership
- **THEN** the membership is removed
- **AND** the user loses project access

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
