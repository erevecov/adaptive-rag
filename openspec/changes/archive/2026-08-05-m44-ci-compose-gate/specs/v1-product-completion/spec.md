## ADDED Requirements

### Requirement: Continuous integration covers backend frontend and OpenSpec

The repository MUST provide a GitHub Actions workflow that runs backend lint/type
checks and tests, frontend test/typecheck/lint/build, and OpenSpec strict
validation without requiring live hosted providers.

#### Scenario: CI workflow encodes required gates

- **WHEN** a reviewer inspects `.github/workflows/ci.yml`
- **THEN** it runs ruff, mypy, and pytest for the Python package
- **AND** runs frontend test, typecheck, lint, and build
- **AND** validates OpenSpec without mandatory live Qwen credentials

### Requirement: Compose demo includes frontend surface

Local compose MUST document/start a frontend service usable with the API and
postgres stack after applying Alembic migrations.

#### Scenario: Compose defines frontend service

- **WHEN** a user opens `compose.yaml`
- **THEN** a `frontend` service is defined that serves the built UI
- **AND** comments document migration steps before demo use
