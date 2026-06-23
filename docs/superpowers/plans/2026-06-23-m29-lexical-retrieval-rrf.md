# M29 Lexical Retrieval RRF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add opt-in local lexical retrieval and dense+lexical RRF before frontend polish.

**Architecture:** Add a focused `LexicalRetriever`, extend `RetrievalService`
with `lexical` and `hybrid_rrf`, serialize strategy score metadata, and expose
strategy selection through API, CLI and offline evals.

**Tech Stack:** SQLAlchemy, PostgreSQL full-text functions, SQLite test
fallback, Typer, FastAPI/Pydantic, OpenSpec.

---

### Task 1: OpenSpec and Docs

**Files:**
- Create: `openspec/changes/m29-lexical-retrieval-rrf/*`
- Create: `docs/superpowers/specs/2026-06-23-m29-lexical-rrf-design.md`
- Create: `docs/superpowers/plans/2026-06-23-m29-lexical-retrieval-rrf.md`
- Modify: `docs/progress.md`
- Modify: `docs/roadmap.md`

- [x] Archive M28.
- [x] Add M29 OpenSpec change and validate it.
- [x] Mark M29 active in progress/roadmap.

### Task 2: Lexical Retriever

**Files:**
- Create: `tests/unit/retrieval/test_lexical_retriever.py`
- Create: `src/adaptive_rag/retrieval/lexical.py`
- Modify: `src/adaptive_rag/retrieval/__init__.py`

- [x] Write failing lexical ranking and filter tests.
- [x] Verify the tests fail because `LexicalRetriever` is missing.
- [x] Implement lexical search and SQLite fallback.
- [x] Verify lexical tests pass.

### Task 3: Service and RRF

**Files:**
- Modify: `tests/unit/retrieval/test_retrieval_service.py`
- Modify: `src/adaptive_rag/retrieval/service.py`
- Modify: `src/adaptive_rag/retrieval/payloads.py`
- Modify: `src/adaptive_rag/api/schemas/retrieval.py`

- [x] Add failing service tests for `lexical` and `hybrid_rrf`.
- [x] Implement strategy enum, lexical path and RRF fusion.
- [x] Add optional `retrieval_metadata` serialization.
- [x] Verify service tests pass.

### Task 4: Public Surfaces and Evals

**Files:**
- Modify: `tests/integration/api/test_retrieval.py`
- Modify: `tests/integration/cli/test_retrieval_cli.py`
- Modify: `tests/integration/cli/test_evals_cli.py`
- Modify: `src/adaptive_rag/cli/evals.py`
- Modify: `src/adaptive_rag/evals/runner.py`
- Modify: `src/adaptive_rag/evals/retrieval_runner.py`
- Modify: `src/adaptive_rag/chat/audit.py`

- [x] Add failing API/CLI/eval tests for strategy selection.
- [x] Expose `--retrieval-strategy` for offline evals.
- [x] Preserve lexical/RRF scores in audit.
- [x] Verify targeted tests pass.

### Task 5: Validation and PR

**Files:**
- All touched files.

- [x] Run `uv run pytest`.
- [x] Run `uv run ruff check .`.
- [x] Run `uv run mypy src`.
- [x] Run OpenSpec validation and `git diff --check`.
- [x] Commit, push and open a draft PR.
