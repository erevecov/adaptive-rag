# M27 Retrieval Expansion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Open the post-v1 retrieval expansion track so contextual retrieval, lexical/RRF and sparse retrieval can be completed before frontend polish.

**Architecture:** Create an OpenSpec planning change that keeps `dense` as default and sequences advanced retrieval as opt-in capabilities. The change updates docs and retrieval-quality requirements without touching runtime ranking code.

**Tech Stack:** OpenSpec, Markdown docs, existing Adaptive RAG retrieval specs.

---

### Task 1: Planning Scope

**Files:**
- Create: `docs/superpowers/specs/2026-06-23-post-v1-retrieval-expansion-design.md`
- Create: `docs/superpowers/plans/2026-06-23-m27-retrieval-expansion-plan.md`

- [ ] Record the approved opt-in/evidence-driven design.
- [ ] Declare the M28-M31 sequence before implementation work begins.

### Task 2: OpenSpec Change

**Files:**
- Create: `openspec/changes/m27-retrieval-expansion-plan/proposal.md`
- Create: `openspec/changes/m27-retrieval-expansion-plan/design.md`
- Create: `openspec/changes/m27-retrieval-expansion-plan/tasks.md`
- Create: `openspec/changes/m27-retrieval-expansion-plan/specs/retrieval-quality/spec.md`

- [ ] Add an OpenSpec change for post-v1 retrieval expansion.
- [ ] Add retrieval-quality requirements for opt-in sequencing and promotion gates.
- [ ] Validate the active change with `npx --yes @fission-ai/openspec validate m27-retrieval-expansion-plan --strict`.

### Task 3: Roadmap and Progress

**Files:**
- Modify: `docs/progress.md`
- Modify: `docs/roadmap.md`
- Create: `docs/architecture/post-v1-retrieval-expansion-m27.md`

- [ ] Mark M27 as active.
- [ ] Add M28 Contextual Retrieval, M29 Lexical/RRF, M30 Qwen sparse and M31 Retrieval strategy gate.
- [ ] State that frontend polish follows after backend capabilities stabilize.

### Task 4: Validation and PR

**Files:**
- All M27 docs and OpenSpec files.

- [ ] Run OpenSpec validation.
- [ ] Run docs-safe checks available locally.
- [ ] Commit, push and open a draft PR.
