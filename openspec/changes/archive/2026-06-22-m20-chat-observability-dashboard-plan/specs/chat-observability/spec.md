# Delta for chat-observability

## ADDED Requirements

### Requirement: Chat observability supports a read-only frontend dashboard

The system MUST allow a frontend dashboard to consume chat observability
summaries without changing the read-only audit trail contract.

#### Scenario: Dashboard consumes the existing project summary

- **WHEN** the frontend requests
  `GET /projects/{project_id}/chat/observability/summary`
- **THEN** the system returns the existing stable summary fields for filters,
  sessions, provider usage and errors
- **AND** applies the same project, `created_at_from`, `created_at_to` and
  `status` filters as the API/CLI contract
- **AND** does not create or modify sessions, messages, tool calls, retrieval
  runs or provider usage

#### Scenario: Dashboard derivations stay faithful to source aggregates

- **WHEN** the dashboard renders metric cards, breakdowns or tables from the
  summary
- **THEN** labels and values MUST reflect the source aggregate they use
- **AND** the system MUST NOT represent per-group latency percentiles as a
  global percentile unless the backend exposes that global aggregate
- **AND** missing cost, token or latency data remains visible instead of being
  invented client-side

#### Scenario: Chart-friendly additions are backward-compatible

- **WHEN** a later M20 slice extends the summary for chart-friendly fields such
  as time buckets or global latency aggregates
- **THEN** existing response fields remain backward-compatible
- **AND** added fields are derived from existing chat audit tables for the same
  project and filters
- **AND** no new mandatory tables, materialized views, exporters hosted or
  telemetry services are required

#### Scenario: Dashboard summary stays safe

- **WHEN** the dashboard displays observability data
- **THEN** it may show aggregate counts, costs, latency summaries, statuses and
  backend-truncated error messages
- **AND** it MUST NOT expose full user messages, full assistant answers, raw
  provider payloads, prompts, API keys or secrets
