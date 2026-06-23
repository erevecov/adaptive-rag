## ADDED Requirements

### Requirement: Frontend polish is workflow-first

The frontend MUST present the existing local product workflows as a coherent
workspace instead of a marketing landing page or a collection of disconnected
demos.

#### Scenario: Product workspace is the first screen

- **WHEN** a user opens the frontend
- **THEN** the first useful screen gives access to project context, authoring,
  ingestion, chat, history and observability workflows
- **AND** it does not require the user to pass through a marketing landing page
  before doing product work

#### Scenario: Workflow navigation preserves project context

- **WHEN** a user selects or creates a project
- **THEN** authoring, ingestion, chat, history and observability surfaces reuse
  the same project context
- **AND** changing workflow views does not silently clear valid project/source
  inputs or chat draft text

### Requirement: Frontend polish covers operational states

The frontend MUST include user-visible states for the normal and failure paths
of authoring, ingestion, chat, history and observability.

#### Scenario: Requests expose stable states

- **WHEN** a frontend request is empty, loading, successful, rejected by HTTP
  validation or blocked by network/backend unavailability
- **THEN** the UI shows a clear state for that condition
- **AND** preserves valid user input when the request fails

#### Scenario: Streaming and ingestion expose in-progress states

- **WHEN** chat streaming or ingestion work is in progress
- **THEN** the UI exposes progress, cancellation or retry affordances according
  to the existing public contracts
- **AND** it does not invent a successful chat answer, citation or ingestion
  result when the backend did not return one

### Requirement: Frontend retrieval polish keeps dense default

The frontend MUST keep `dense` as the default retrieval experience for M32 and
MUST NOT promote advanced retrieval modes into the default UI.

#### Scenario: Default chat uses dense retrieval

- **WHEN** a user sends a normal chat question without selecting experimental
  controls
- **THEN** the frontend uses the backend default retrieval strategy
- **AND** the backend default remains `dense`

#### Scenario: Advanced modes are not default controls

- **WHEN** M32 frontend polish is implemented
- **THEN** `contextual_dense`, `lexical`, `hybrid_rrf`, `dense_sparse`,
  `dense_rerank` and `graph` are not presented as default product controls
- **AND** any later exposure is opt-in, clearly experimental and consistent
  with M31 strategy-gate decisions

### Requirement: Frontend polish has visual QA criteria

The frontend MUST define visual and interaction QA criteria before M32 is
closed.

#### Scenario: Responsive QA is required

- **WHEN** a M32 implementation slice changes frontend screens
- **THEN** the slice validates affected workflows on desktop and mobile
  viewports
- **AND** checks for console errors, broken layout, overlapping text and
  unreadable controls before the slice is considered complete

#### Scenario: Documentation follows user-facing workflow changes

- **WHEN** frontend polish changes the local first-run or dev workflow
- **THEN** the affected README or runbook instructions are updated in the same
  milestone sequence
