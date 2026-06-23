# M26 V1 Product Quality Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the first-run product flow into final v1.0 release evidence with a public quality-gate command, docs and OpenSpec closeout.

**Architecture:** Add a small `adaptive_rag.v1_quality_gate` orchestration module plus a thin `adaptive-rag v1 quality-gate` CLI wrapper. The gate reuses M25 first-run orchestration, evaluates explicit release criteria, and emits a machine-readable report without changing retrieval/provider defaults.

**Tech Stack:** Python 3.12, Typer, SQLAlchemy, existing Adaptive RAG first-run services, OpenSpec, pytest, Ruff, mypy.

---

### Task 1: OpenSpec and Plan

**Files:**
- Create: `openspec/changes/m26-v1-product-quality-gate/proposal.md`
- Create: `openspec/changes/m26-v1-product-quality-gate/design.md`
- Create: `openspec/changes/m26-v1-product-quality-gate/tasks.md`
- Create: `openspec/changes/m26-v1-product-quality-gate/specs/v1-product-completion/spec.md`
- Create: `openspec/changes/m26-v1-product-quality-gate/specs/v1-release-readiness/spec.md`
- Create: `docs/superpowers/plans/2026-06-23-m26-v1-product-quality-gate.md`

- [ ] Validate with `npx --yes @fission-ai/openspec validate m26-v1-product-quality-gate --strict`.

### Task 2: V1 Quality Gate Service and CLI

**Files:**
- Create: `src/adaptive_rag/v1_quality_gate.py`
- Create: `src/adaptive_rag/cli/v1.py`
- Modify: `src/adaptive_rag/cli/app.py`
- Test: `tests/integration/cli/test_v1_quality_gate_cli.py`

- [ ] Add a failing CLI test for `adaptive-rag v1 quality-gate`.
- [ ] Implement `V1QualityGateReport` and `run_v1_quality_gate()`.
- [ ] Register `v1` in the root Typer app.
- [ ] Verify the command emits first-run evidence, release criteria and decision.

### Task 3: Docs and Release Runbook

**Files:**
- Create: `docs/v1-quality-gate.md`
- Modify: `README.md`
- Test: `tests/unit/test_v1_quality_gate_docs.py`

- [ ] Add failing docs tests for the quality-gate command, evidence fields and opt-in boundaries.
- [ ] Add the v1 quality-gate runbook with setup, expected JSON and manual tag boundary.
- [ ] Refresh README so the final v1 gate points to the runbook and command.

### Task 4: Archive and Closeout

**Files:**
- Modify: `docs/progress.md`
- Modify: `docs/roadmap.md`
- Archive: `openspec/changes/m26-v1-product-quality-gate/`

- [ ] Run backend/frontend/OpenSpec validation.
- [ ] Archive the M26 change.
- [ ] Update progress/roadmap to mark v1 product quality gate complete and no next product-gap milestone pending.
