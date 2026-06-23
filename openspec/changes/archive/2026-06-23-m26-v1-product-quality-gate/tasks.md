# Tasks M26 v1 product quality gate

## 1. Planning and setup

- [x] 1.1 Confirm PR #120 is merged in `origin/main`.
- [x] 1.2 Create branch `codex/m26-v1-product-quality-gate` from `origin/main`.
- [x] 1.3 Confirm `openspec list` has no active changes after M25.
- [x] 1.4 Validate the M25 first-run contract and release-readiness specs.

## 2. OpenSpec

- [x] 2.1 Add proposal, design and tasks for `m26-v1-product-quality-gate`.
- [x] 2.2 Add deltas for `v1-product-completion` and `v1-release-readiness`.
- [x] 2.3 Validate the active change with `openspec validate --strict`.

## 3. V1 quality gate CLI

- [x] 3.1 Add failing CLI tests for `adaptive-rag v1 quality-gate`.
- [x] 3.2 Implement the quality-gate orchestration service and CLI command.
- [x] 3.3 Confirm the report includes first-run evidence, criteria and decision.
- [x] 3.4 Confirm the command can write the report to `--output`.

## 4. Docs and release runbook

- [x] 4.1 Add failing docs tests for README/runbook required commands and fields.
- [x] 4.2 Add `docs/v1-quality-gate.md` with setup, command, expected JSON and manual release notes.
- [x] 4.3 Update README to make the quality gate the final v1 product gate.

## 5. Quality gate and archive

- [x] 5.1 Validate backend with pytest, Ruff and mypy.
- [x] 5.2 Validate frontend with Vitest, typecheck, lint and build.
- [x] 5.3 Validate OpenSpec active and canonical specs.
- [x] 5.4 Archive `m26-v1-product-quality-gate`.
- [x] 5.5 Update `docs/progress.md` and `docs/roadmap.md` to close M26.
