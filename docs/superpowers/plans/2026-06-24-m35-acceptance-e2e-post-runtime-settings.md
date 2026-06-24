# M35 Acceptance E2E Post Runtime Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a public acceptance smoke that proves persisted runtime settings and model catalog are used by the local end-to-end product flow.

**Architecture:** Add a focused `adaptive_rag.acceptance` runner plus a thin `adaptive-rag acceptance runtime-settings-smoke` CLI wrapper. The runner configures fake provider runtime settings in the database, syncs the fake model catalog, creates a project override, resolves effective providers from persisted settings, and emits JSON evidence.

**Tech Stack:** Python 3.12, Typer, SQLAlchemy, existing first-run services, provider runtime repositories, OpenSpec, pytest, Ruff.

---

### Task 1: OpenSpec Contract

**Files:**
- Create: `openspec/changes/m35-acceptance-e2e-post-runtime-settings/proposal.md`
- Create: `openspec/changes/m35-acceptance-e2e-post-runtime-settings/design.md`
- Create: `openspec/changes/m35-acceptance-e2e-post-runtime-settings/tasks.md`
- Create: `openspec/changes/m35-acceptance-e2e-post-runtime-settings/specs/provider-runtime/spec.md`
- Create: `openspec/changes/m35-acceptance-e2e-post-runtime-settings/specs/v1-product-completion/spec.md`

- [x] Add a provider-runtime requirement for runtime settings acceptance.
- [x] Add a v1-product-completion requirement for post-runtime-settings acceptance.
- [x] Validate with `npx --yes @fission-ai/openspec validate m35-acceptance-e2e-post-runtime-settings --strict`.

### Task 2: Acceptance CLI TDD

**Files:**
- Create: `tests/integration/cli/test_acceptance_cli.py`
- Create: `src/adaptive_rag/acceptance.py`
- Create: `src/adaptive_rag/cli/acceptance.py`
- Modify: `src/adaptive_rag/cli/app.py`

- [x] Add a failing CLI test for `adaptive-rag acceptance runtime-settings-smoke`.
- [x] Verify it fails because the command/module does not exist.
- [x] Implement the runner and CLI wrapper.
- [x] Verify the focused CLI test passes.

### Task 3: Runtime Acceptance Runbook

**Files:**
- Create: `tests/unit/test_acceptance_docs.py`
- Create: `docs/runtime-acceptance.md`
- Modify: `README.md`

- [x] Add failing docs tests for the runbook and README link.
- [x] Add `docs/runtime-acceptance.md` with setup, command, expected JSON and opt-in boundaries.
- [x] Update README to point to the new smoke.
- [x] Verify docs tests pass.

### Task 4: Closeout

**Files:**
- Modify: `docs/progress.md`
- Modify: `docs/roadmap.md`
- Archive: `openspec/changes/m35-acceptance-e2e-post-runtime-settings/`

- [ ] Run full backend, frontend and OpenSpec gates.
- [ ] Archive M35 after all tasks are complete.
- [ ] Update progress/roadmap to M35 complete.
- [ ] Commit, push and open PR.
