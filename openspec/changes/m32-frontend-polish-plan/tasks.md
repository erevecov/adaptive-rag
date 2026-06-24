# Tasks M32 frontend polish plan

## 1. Setup

- [x] 1.1 Confirm PR #127 is merged in `origin/main`.
- [x] 1.2 Create branch `codex/m32-frontend-polish-plan`.
- [x] 1.3 Confirm no active OpenSpec changes exist.
- [x] 1.4 Add OpenSpec proposal, design, tasks and spec deltas.

## 2. Frontend polish scope

- [x] 2.1 Inventory product workflows already backed by public contracts.
- [x] 2.2 Define required empty/loading/success/error and operational states.
- [x] 2.3 Declare `dense` as the default frontend retrieval path.
- [x] 2.4 Keep advanced retrieval modes opt-in/experimental unless a future gate
  promotes them.

## 3. Docs

- [x] 3.1 Update `docs/progress.md` to make M32 active.
- [x] 3.2 Update `docs/roadmap.md` with M32 sequencing and constraints.

## 4. Validation and PR

- [x] 4.1 Run OpenSpec validation for `m32-frontend-polish-plan`.
- [x] 4.2 Run canonical spec validation and diff hygiene checks.
- [x] 4.3 Commit, push and open a draft PR.

## 5. Product shell and authoring polish

- [x] 5.1 Add tests for selected project context across workspace views.
- [x] 5.2 Add tests for explicit source-to-ingestion next steps.
- [x] 5.3 Add tests for ingestion job attempts, scheduling and lock state.
- [x] 5.4 Add a compact project context bar shared by authoring, chat and
  observability.
- [x] 5.5 Polish source rows and ingestion run/job state without changing API
  contracts or retrieval defaults.

## 6. Validation for product shell and authoring

- [x] 6.1 Run frontend unit tests.
- [x] 6.2 Run frontend lint, typecheck and build.
- [x] 6.3 Run OpenSpec validation.
- [x] 6.4 Run responsive browser QA for authoring and shell views.
