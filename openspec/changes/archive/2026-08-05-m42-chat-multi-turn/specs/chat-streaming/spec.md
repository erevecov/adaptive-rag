## ADDED Requirements

### Requirement: Streaming chat accepts session_id

`POST /projects/{project_id}/chat/stream` MUST accept the same optional
`session_id` contract as non-stream chat.

#### Scenario: Stream follow-up continues session

- **WHEN** a client streams a follow-up with an existing `session_id`
- **THEN** the stream emits `session_started` (or equivalent) with that id
- **AND** the final event returns the same `session_id`
