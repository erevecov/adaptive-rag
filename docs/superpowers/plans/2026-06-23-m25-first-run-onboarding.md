# M25 First-Run Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible local first-run path that creates user/sample data, ingests it, indexes it and returns cited chat evidence from public commands.

**Architecture:** Add a focused `adaptive_rag.first_run` orchestration module and thin `adaptive-rag first-run smoke` CLI wrapper. Reuse existing authoring, ingestion ops, chunking, dense embedding and chat services so M25 proves the default product flow without adding a broader indexing/admin surface.

**Tech Stack:** Python 3.12, Typer, SQLAlchemy, existing Adaptive RAG repositories/services, OpenSpec, pytest, Ruff, mypy.

---

### Task 1: OpenSpec and Plan

**Files:**
- Create: `openspec/changes/m25-first-run-onboarding/proposal.md`
- Create: `openspec/changes/m25-first-run-onboarding/design.md`
- Create: `openspec/changes/m25-first-run-onboarding/tasks.md`
- Create: `openspec/changes/m25-first-run-onboarding/specs/first-run-onboarding/spec.md`
- Create: `openspec/changes/m25-first-run-onboarding/specs/v1-product-completion/spec.md`
- Create: `openspec/changes/m25-first-run-onboarding/specs/chat-frontend/spec.md`
- Create: `docs/superpowers/plans/2026-06-23-m25-first-run-onboarding.md`

- [ ] Validate with `npx --yes @fission-ai/openspec validate m25-first-run-onboarding --strict`.

### Task 2: First-Run Service and CLI

**Files:**
- Create: `src/adaptive_rag/first_run.py`
- Create: `src/adaptive_rag/cli/first_run.py`
- Modify: `src/adaptive_rag/cli/app.py`
- Test: `tests/integration/cli/test_first_run_cli.py`

- [ ] Add a failing CLI test for `adaptive-rag first-run smoke`.
- [ ] Implement `FirstRunReport` and `run_first_run_smoke()`.
- [ ] Register `first-run` in the root Typer app.
- [ ] Verify the command creates project/source/job/version/chunks/embeddings and citations.

### Task 3: Docs and Runbook

**Files:**
- Create: `docs/first-run.md`
- Modify: `README.md`
- Test: `tests/unit/test_first_run_docs.py`

- [ ] Add failing docs tests for the required command sequence and opt-in boundaries.
- [ ] Add first-run runbook with local setup, migrations, smoke command and expected JSON.
- [ ] Refresh README so first-run is the default local product path.

### Task 4: Archive and Closeout

**Files:**
- Modify: `docs/progress.md`
- Modify: `docs/roadmap.md`
- Archive: `openspec/changes/m25-first-run-onboarding/`

- [ ] Run backend/frontend/OpenSpec validation.
- [ ] Archive the M25 change.
- [ ] Update progress/roadmap to make M26 the next recommended milestone.
