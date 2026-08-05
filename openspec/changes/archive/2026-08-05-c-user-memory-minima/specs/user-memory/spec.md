# user-memory Specification

## Purpose

Durable user memory with explicit approval before chat injection.

## Requirements

### Requirement: User memories are stored durably with approval states

The system MUST persist user memory items with status `proposed`, `approved`,
or `rejected`.

#### Scenario: Propose then approve

- **WHEN** a user proposes memory content
- **THEN** it is stored as `proposed`
- **AND** after approval status is `approved`

### Requirement: Only approved memories are injectable

#### Scenario: Injection text excludes non-approved

- **WHEN** injection text is requested
- **THEN** only `approved` memories for the user (and project/global scope) appear
