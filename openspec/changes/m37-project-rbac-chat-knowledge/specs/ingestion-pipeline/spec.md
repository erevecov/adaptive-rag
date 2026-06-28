## ADDED Requirements

### Requirement: Approved knowledge proposals feed ingestion

The system MUST convert approved knowledge proposals into explicit source
ingestion work for the same project.

#### Scenario: Approval creates source and ingestion job

- **GIVEN** a pending knowledge proposal in project `P`
- **WHEN** a contributor approves it
- **THEN** the system creates a text source in project `P` using the approved
  proposal text
- **AND** records the created source id on the proposal
- **AND** enqueues an `ingest_source` job for that source

#### Scenario: Refined approval uses refined text

- **GIVEN** a pending proposal has `proposed_text` and `refined_text`
- **WHEN** a contributor approves it
- **THEN** the created source uses `refined_text` as canonical content
- **AND** preserves the original proposed text in proposal/audit metadata

#### Scenario: Rejected proposal does not ingest

- **GIVEN** a pending proposal
- **WHEN** a contributor rejects it with a reason
- **THEN** no source, document version, chunk, embedding or ingestion job is
  created from that proposal

#### Scenario: Pending proposals are not retrievable

- **GIVEN** a viewer submitted a pending proposal
- **WHEN** retrieval or chat runs for that project before approval
- **THEN** the pending proposal text is not included in retrieval candidates

### Requirement: Knowledge review actions are audited

The system MUST preserve who submitted and who reviewed each proposal.

#### Scenario: Approval records reviewer

- **WHEN** a contributor approves a proposal
- **THEN** the proposal records `reviewed_by_user_id`, `reviewed_at` and final
  status

#### Scenario: Rejection requires reason

- **WHEN** a contributor rejects a proposal
- **THEN** the request requires a non-empty reason
- **AND** the reason is stored for future review
