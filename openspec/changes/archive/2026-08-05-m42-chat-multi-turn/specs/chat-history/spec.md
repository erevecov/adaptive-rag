## ADDED Requirements

### Requirement: Multi-turn history remains consistent on read-back

Continued sessions MUST expose appended turns via the existing session detail
surface in deterministic order.

#### Scenario: History read-back after follow-up

- **WHEN** two chat turns run with the same `session_id`
- **THEN** session detail lists both user messages and both assistant answers
  in creation order
