# Tasks M25 first-run onboarding

## 1. Planning and setup

- [x] 1.1 Confirm PR #119 is merged in `origin/main`.
- [x] 1.2 Create branch `codex/m25-first-run-onboarding` from `origin/main`.
- [x] 1.3 Confirm `openspec list` has no active changes after M24.
- [x] 1.4 Validate existing CLI, ingestion, chunking, embedding and chat paths.

## 2. OpenSpec

- [x] 2.1 Add proposal, design and tasks for `m25-first-run-onboarding`.
- [x] 2.2 Add new capability `first-run-onboarding`.
- [x] 2.3 Add deltas for `v1-product-completion` and `chat-frontend`.
- [x] 2.4 Validate the active change with `openspec validate --strict`.

## 3. First-run CLI

- [x] 3.1 Add failing CLI tests for `adaptive-rag first-run smoke`.
- [x] 3.2 Implement the first-run orchestration service and CLI command.
- [x] 3.3 Confirm the smoke creates project/source/job/version/chunks/embeddings.
- [x] 3.4 Confirm the smoke emits cited chat evidence and stable failures.

## 4. Docs and runbook

- [x] 4.1 Add failing docs tests for README/runbook required commands.
- [x] 4.2 Add `docs/first-run.md` with setup, migrations, smoke and expected JSON.
- [x] 4.3 Update README to make first-run the default local product path.

## 5. Quality gate and archive

- [x] 5.1 Validate backend with pytest, Ruff and mypy.
- [x] 5.2 Validate frontend with Vitest, typecheck, lint and build.
- [x] 5.3 Validate OpenSpec active and canonical specs.
- [x] 5.4 Archive `m25-first-run-onboarding`.
- [x] 5.5 Update `docs/progress.md` and `docs/roadmap.md` toward M26.
