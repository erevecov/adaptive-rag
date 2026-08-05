## ADDED Requirements

### Requirement: Frontend continues the selected session

The chat UI MUST send `session_id` when a session is selected so follow-up
questions stay on that conversation.

#### Scenario: Selected session is included in chat request body

- **WHEN** the user has a selected session and submits a question
- **THEN** the chat request body includes that `session_id`
- **AND** the selected session remains selected after a successful answer
