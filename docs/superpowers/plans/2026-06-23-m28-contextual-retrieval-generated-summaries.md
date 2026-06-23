# M28 Contextual Retrieval Generated Summaries

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development while implementing this plan. Keep checkboxes current as tasks complete.

**Goal:** Generate and persist `contextual_summary` during local indexing so
the existing dense embedding input path can use contextualized chunks before
frontend polish starts.

**Architecture:** Add a local deterministic contextualizer and
project-scoped pipeline. Wire first-run after chunking and before dense
embedding. Keep retrieval strategy selection unchanged.

**Tech Stack:** SQLAlchemy repositories, existing chunking and dense embedding
pipelines, Typer first-run CLI, OpenSpec.

---

### Task 1: OpenSpec and Docs

**Files:**
- Create: `openspec/changes/m28-contextual-retrieval-generated-summaries/*`
- Modify: `docs/progress.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/first-run.md`

- [x] Add M28 proposal, design, tasks and spec deltas.
- [x] Mark M27 archived and M28 active in docs.
- [x] Document first-run contextualized evidence fields.

### Task 2: Pipeline Tests

**Files:**
- Create: `tests/unit/test_contextualization.py`

- [x] Test deterministic generated summaries.
- [x] Test project-scoped persistence.
- [x] Test idempotency for existing summaries.
- [x] Test cross-project rejection.

### Task 3: Implementation

**Files:**
- Create: `src/adaptive_rag/contextualization.py`
- Modify: `src/adaptive_rag/db/repositories/chunks.py`

- [x] Add contextualizer output/result dataclasses.
- [x] Add deterministic local contextualizer.
- [x] Add pipeline that fills missing summaries and returns counts.
- [x] Add repository method for updating `contextual_summary`.

### Task 4: First-Run Integration

**Files:**
- Modify: `src/adaptive_rag/first_run.py`
- Modify: `tests/integration/cli/test_first_run_cli.py`
- Modify: `docs/v1-quality-gate.md`

- [x] Add report counts.
- [x] Call contextualization before embedding.
- [x] Assert CLI JSON exposes the new fields.

### Task 5: Validation and PR

**Files:**
- All touched files.

- [x] Run targeted tests.
- [x] Run `uv run ruff check .`, `uv run mypy src` and OpenSpec validation.
- [x] Commit, push and open a draft PR.
