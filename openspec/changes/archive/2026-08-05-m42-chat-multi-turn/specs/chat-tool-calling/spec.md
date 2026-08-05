## ADDED Requirements

### Requirement: Chat requests may continue a session

`POST /projects/{project_id}/chat` and stream MUST accept optional `session_id`
and continue that session when it belongs to the project (and user when scoped).

#### Scenario: Follow-up reuses session_id

- **WHEN** a client posts a chat message with `session_id` of an existing session
- **THEN** the response uses the same `session_id`
- **AND** new user/assistant messages append to that session history

#### Scenario: Missing session_id starts a new session

- **WHEN** a client posts chat without `session_id`
- **THEN** a new session is created and returned

### Requirement: Runner receives bounded history and condensed retrieval query

The chat service MUST load a bounded prior history for continued sessions and
condense a retrieval query with a deterministic condenser available for tests.

#### Scenario: Follow-up retrieval uses condensed query

- **WHEN** a continued session has prior user/assistant turns
- **THEN** the runner request includes bounded history
- **AND** retrieval is invoked with a condensed self-contained query
