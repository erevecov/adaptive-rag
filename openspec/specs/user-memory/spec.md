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

The system MUST include only `approved` memories in chat injection text.

#### Scenario: Injection text excludes non-approved

- **WHEN** injection text is requested
- **THEN** only `approved` memories for the user (and project/global scope) appear

### Requirement: Proposed memories MAY be edited before review

The system SHALL allow the owning user to PATCH content of a memory while its
status is `proposed`. Edits of `approved` or `rejected` memories MUST return
conflict (409).

#### Scenario: Edit proposed content

- **WHEN** the owner PATCHes content on a `proposed` memory
- **THEN** the stored content is updated and status remains `proposed`

### Requirement: Approved memories MAY be soft-removed via reject

Rejecting an `approved` memory SHALL transition it to `rejected` and remove it
from injection text. This reuses the existing status set (no `archived` status).

#### Scenario: Soft-remove approved memory

- **WHEN** the owner rejects an `approved` memory
- **THEN** status becomes `rejected`
- **AND** injection text no longer includes that content

### Requirement: Soft-removed memories MAY be restored via approve

Approving a `rejected` memory SHALL transition it to `approved` and restore it
to injection text. This reuses the existing status set (no fourth status) so
soft-remove undo does not require re-propose.

#### Scenario: Restore rejected memory to approved

- **WHEN** the owner approves a `rejected` memory
- **THEN** status becomes `approved`
- **AND** injection text includes that content again
