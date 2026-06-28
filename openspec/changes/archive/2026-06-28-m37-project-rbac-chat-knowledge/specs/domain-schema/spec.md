## ADDED Requirements

### Requirement: Domain schema supports local users and project memberships

The system MUST persist local users and project memberships so project access
can be authorized without relying on external auth providers.

#### Scenario: User records carry system role and active state

- **WHEN** a user is created
- **THEN** the row stores a stable id, unique login identifier, display name,
  `system_role`, `is_active`, `created_at` and `updated_at`
- **AND** `system_role` is constrained to `superadmin` or `user`

#### Scenario: Project membership records carry project role

- **WHEN** a user is assigned to a project
- **THEN** the membership stores `project_id`, `user_id`, role and timestamps
- **AND** role is constrained to `admin`, `contributor` or `viewer`
- **AND** active duplicate memberships for the same user/project are rejected

### Requirement: Chat sessions belong to a user

The system MUST persist the owner user on every chat session.

#### Scenario: New chat session stores user id

- **WHEN** an authenticated user starts a chat in a project
- **THEN** the new `chat_sessions` row stores both `project_id` and `user_id`
- **AND** downstream messages, tool calls and retrieval runs remain linked to
  that session

#### Scenario: Existing session indexes support user-scoped listing

- **WHEN** chat sessions are listed for a project and user
- **THEN** the schema supports efficient filtering by `project_id`, `user_id`
  and `created_at`

### Requirement: Knowledge proposals preserve chat origin before ingestion

The system MUST persist chat-sourced knowledge proposals separately from
approved sources/documents/chunks.

#### Scenario: Viewer proposal starts pending

- **WHEN** a viewer proposes knowledge from chat
- **THEN** a `knowledge_proposals` row is created with `status = "pending"`
- **AND** it stores project, submitter, proposed text and chat origin

#### Scenario: Approved proposal records reviewer and source

- **WHEN** a contributor or admin approves a proposal
- **THEN** the proposal stores `status = "approved"`, reviewer, reviewed time
  and the source id created for ingestion

#### Scenario: Rejected proposal records reason

- **WHEN** a contributor or admin rejects a proposal
- **THEN** the proposal stores `status = "rejected"`, reviewer, reviewed time
  and a non-empty rejection reason
