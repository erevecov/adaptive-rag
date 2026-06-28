## ADDED Requirements

### Requirement: Chat requests execute as the current project user

The system MUST bind every chat request to an authenticated user and project
role before running retrieval or model calls.

#### Scenario: Viewer can start private chat session

- **GIVEN** the current user has project role `viewer`
- **WHEN** they send a chat request for that project
- **THEN** the chat service creates a session owned by that user
- **AND** retrieval uses only approved knowledge from that project
- **AND** the response includes the created session id

#### Scenario: Locked project chat is rejected before providers

- **GIVEN** the current user has no access to a project
- **WHEN** they send a chat request for that project
- **THEN** the request is rejected before retrieval, embeddings or chat
  providers are called

### Requirement: Chat can propose knowledge with auditable origin

The system MUST let users propose new project knowledge from a chat context
without making pending proposals retrievable.

#### Scenario: Viewer proposal remains pending

- **GIVEN** a viewer is chatting in a project
- **WHEN** they propose knowledge from a chat message
- **THEN** the system creates a pending knowledge proposal linked to the
  project, session, message and submitter
- **AND** the proposal does not create chunks or embeddings until approved

#### Scenario: Contributor proposal is approved directly

- **GIVEN** a contributor is chatting in a project
- **WHEN** they propose knowledge from a chat message
- **THEN** the system records an approved proposal or equivalent audit record
- **AND** creates approved source input for ingestion without human review

#### Scenario: Proposal origin is available to reviewers

- **GIVEN** a pending proposal was created from chat
- **WHEN** a contributor opens proposal detail
- **THEN** the response includes enough origin metadata to navigate to the
  source session/message context without exposing unrelated private sessions
