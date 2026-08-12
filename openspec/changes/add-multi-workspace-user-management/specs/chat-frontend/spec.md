## ADDED Requirements

### Requirement: Frontend has a human session boundary

The frontend MUST authenticate humans through server cookies and render login or
mandatory password change before protected application surfaces.

#### Scenario: Unauthenticated startup shows login

- **WHEN** `/auth/me` returns an authentication error
- **THEN** the application renders email and password login
- **AND** no configured bearer token is required in the browser

#### Scenario: Temporary password blocks application

- **GIVEN** the current user must change password
- **WHEN** the application initializes
- **THEN** only the password-change surface and logout are available
- **AND** normal application navigation is hidden
