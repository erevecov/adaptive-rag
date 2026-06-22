# Delta for chat-frontend

## ADDED Requirements

### Requirement: Frontend exposes a read-only chat observability dashboard

The frontend MUST expose a read-only dashboard for chat observability using the
public API contracts already exposed by the backend.

#### Scenario: User filters observability by project and time range

- **WHEN** the user enters a `project_id`, optional `created_at_from`,
  `created_at_to` and `status` filters, then refreshes observability
- **THEN** the frontend calls
  `GET /projects/{project_id}/chat/observability/summary`
- **AND** sends only non-empty public query parameters
- **AND** preserves the filter inputs when the request fails

#### Scenario: Dashboard renders summary cards and breakdowns

- **WHEN** a summary response is loaded
- **THEN** the frontend renders session total, provider usage total, estimated
  known cost, error counts and status breakdowns
- **AND** renders provider usage groups by operation, provider and model
- **AND** labels latency values according to the backend aggregate actually
  used

#### Scenario: Dashboard renders recent session health read-only

- **WHEN** the dashboard needs a recent session health table
- **THEN** the frontend may call `GET /projects/{project_id}/chat/sessions`
  with public list parameters
- **AND** displays only session summary fields such as status, counts,
  timestamps and estimated cost
- **AND** does not replay, edit, delete or re-run chat sessions

#### Scenario: Dashboard handles operational states

- **WHEN** observability data is loading, empty or fails with HTTP/network
  errors
- **THEN** the frontend shows clear loading, empty and error states
- **AND** does not clear valid user filters on failure
- **AND** does not require provider API keys or secrets in the browser

#### Scenario: Dashboard does not expand backend scope

- **WHEN** the frontend observability dashboard is implemented
- **THEN** it remains a client of public API contracts
- **AND** it does not query internal tables directly
- **AND** it does not change retrieval, rerank, provider, streaming or graph
  defaults
