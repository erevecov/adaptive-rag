# Delta for chat-frontend

## MODIFIED Requirements

### Requirement: Frontend polish covers operational states

The frontend MUST include user-visible states for the normal and failure paths
of authoring, ingestion, chat, history and observability.

#### Scenario: Streaming chat shows a response-local stepper

- **WHEN** chat streaming is in progress and the backend emits `step` events
- **THEN** the frontend renders a response-local stepper near the active answer
- **AND** expanded mode shows ordered steps with status, latency and available
  detail or usage fields
- **AND** collapsed mode shows a compact current-phase ticker
- **AND** cancellation or failure does not invent a successful final answer

#### Scenario: Stepper expansion preference is persisted

- **WHEN** the user expands or collapses the chat stepper
- **THEN** the frontend writes the preference to
  `adaptive-rag:chat-stepper-expanded`
- **AND** the next chat turn initializes from that persisted preference
- **AND** storage failures do not break the in-memory toggle state

### Requirement: Chat workspace provides minimap and action stepper

The frontend MUST make persisted conversation and internal action data
navigable without changing backend behavior.

#### Scenario: Finished response rehydrates persisted step metadata

- **WHEN** a selected or reloaded chat session has an assistant message with
  `metadata.steps`
- **THEN** the frontend parses valid step records and renders them under the
  finished response details
- **AND** malformed individual steps are ignored without blanking the answer
- **AND** older sessions without steps keep the legacy answer, citations and
  tool-call rendering
