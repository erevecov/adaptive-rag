## ADDED Requirements

### Requirement: Chat answers are filtered for secret-like content

The system MUST redact secret-like patterns from chat answers on both
non-streaming and streaming paths before the answer is returned to the client
or persisted in chat audit history.

#### Scenario: Non-stream answer redacts secrets

- **WHEN** the chat runner returns an answer containing a secret-like token
- **THEN** the API response answer does not include the original secret literal

#### Scenario: Stream answer_delta and final redact secrets

- **WHEN** a streaming chat turn produces an answer with a secret-like token
- **THEN** `answer_delta` and `final` events expose only the redacted answer
