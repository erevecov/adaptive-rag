## ADDED Requirements

### Requirement: Chat history is private to the current user

The system MUST keep chat sessions private per user within a shared project.

#### Scenario: User lists only own sessions

- **GIVEN** users `A` and `B` both have access to project `P`
- **AND** both users have chat sessions in `P`
- **WHEN** user `A` calls `GET /projects/P/chat/sessions`
- **THEN** the response contains only sessions whose owner is user `A`
- **AND** sessions owned by user `B` are not counted or returned

#### Scenario: User cannot inspect another user's session

- **GIVEN** user `B` owns a chat session in project `P`
- **AND** user `A` also has access to project `P`
- **WHEN** user `A` calls `GET /projects/P/chat/sessions/{session_id}` for
  user `B`'s session
- **THEN** the response is not found or an equivalent privacy-preserving error
- **AND** no messages, tool calls, retrieval runs, citations or provider usage
  from user `B` are returned

#### Scenario: Project switch resets selected session

- **WHEN** the frontend switches from project `A` to project `B`
- **THEN** any selected chat session from project `A` is cleared
- **AND** history reloads under the current user and project `B`

### Requirement: Chat observability respects project role

The system MUST restrict project chat observability to project admins or
superadmins.

#### Scenario: Project admin can inspect aggregate observability

- **GIVEN** the current user has project role `admin`
- **WHEN** they call project chat observability endpoints
- **THEN** aggregate project observability is returned
- **AND** private message bodies from other users are not included

#### Scenario: Viewer cannot inspect project observability

- **GIVEN** the current user has project role `viewer`
- **WHEN** they call project chat observability endpoints
- **THEN** the request fails with a stable project-role authorization error
