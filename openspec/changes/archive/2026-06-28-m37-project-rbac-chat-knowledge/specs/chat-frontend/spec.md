## ADDED Requirements

### Requirement: Frontend uses a searchable project selector with access states

The frontend MUST replace manual project id entry with project discovery that
shows accessible and locked projects.

#### Scenario: Selector shows all project names

- **GIVEN** the project list API returns accessible and locked projects
- **WHEN** the app renders the project selector
- **THEN** all project names are searchable
- **AND** locked projects are visually disabled or marked unavailable
- **AND** locked projects cannot be selected for chat, authoring or ingestion

#### Scenario: Accessible project drives workspace requests

- **WHEN** the user selects an accessible project
- **THEN** chat, session history, source viewer, authoring, ingestion,
  observability and runtime override requests use that project id
- **AND** stale selected sessions from a previous project are cleared

### Requirement: Frontend gates surfaces by effective role

The frontend MUST use the current user's effective role to show only usable
project surfaces while relying on backend authorization as source of truth.

#### Scenario: Viewer sees chat and proposal actions

- **GIVEN** the current user has project role `viewer`
- **WHEN** they open an accessible project
- **THEN** chat is available
- **AND** direct source authoring, ingestion controls, member management and
  knowledge review queue are hidden or disabled
- **AND** proposing knowledge from chat is available

#### Scenario: Contributor sees knowledge review

- **GIVEN** the current user has project role `contributor`
- **WHEN** they open an accessible project
- **THEN** direct source authoring and knowledge review queue are available
- **AND** project member management remains unavailable

#### Scenario: Admin sees project member management

- **GIVEN** the current user has project role `admin`
- **WHEN** they open an accessible project
- **THEN** project member management is available
- **AND** project archive/delete controls are unavailable unless the user is
  also `superadmin`

#### Scenario: Superadmin sees global administration

- **GIVEN** the current user has system role `superadmin`
- **WHEN** they open admin settings
- **THEN** global user management and project creation are available
- **AND** provider secret values are still not shown in the browser

### Requirement: Frontend supports knowledge proposal review

The frontend MUST let contributor-or-higher users review pending chat-sourced
knowledge proposals.

#### Scenario: Reviewer approves proposal

- **GIVEN** a pending proposal exists for the selected project
- **WHEN** a contributor approves it from the review queue
- **THEN** the row updates to approved
- **AND** the UI shows the source or ingestion job created by the backend when
  returned

#### Scenario: Reviewer refines proposal

- **GIVEN** a pending proposal exists
- **WHEN** a contributor edits the proposed text and saves refinement
- **THEN** the refined text is shown as the text that will be approved
- **AND** the original proposal remains visible for context

#### Scenario: Reviewer rejects proposal with reason

- **GIVEN** a pending proposal exists
- **WHEN** a contributor rejects it
- **THEN** the UI requires a non-empty reason
- **AND** removes or marks the item as rejected after the backend confirms
