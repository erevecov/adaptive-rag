# Chat Functional Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a functional chat workspace where session navigation,
context, minimap, action stepper, source inspection, STT and memory decisions
are backed by real contracts and verified feature by feature.

**Architecture:** Use existing public frontend APIs first. The selected
`ChatSessionDetailResponse` becomes the shared data source for messages,
internal actions and selected-session usage. Add backend contracts only when a
feature cannot be truthfully implemented from existing APIs.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, FastAPI,
OpenSpec.

---

### Task 1: OpenSpec and Baseline

**Files:**
- Create: `openspec/changes/m36-chat-functional-workspace/proposal.md`
- Create: `openspec/changes/m36-chat-functional-workspace/design.md`
- Create: `openspec/changes/m36-chat-functional-workspace/tasks.md`
- Create: `openspec/changes/m36-chat-functional-workspace/specs/chat-frontend/spec.md`
- Create: `docs/superpowers/plans/2026-06-28-chat-functional-workspace.md`

- [x] **Step 1: Create isolated worktree**

Run:

```powershell
git worktree add '.worktrees/chat-functional-workspace' -b 'codex/chat-functional-workspace' origin/main
```

Expected: branch created from `origin/main`.

- [x] **Step 2: Install frontend dependencies**

Run:

```powershell
pnpm --dir frontend install --frozen-lockfile
```

Expected: lockfile unchanged and dependencies installed.

- [x] **Step 3: Verify baseline frontend**

Run:

```powershell
pnpm --dir frontend test
pnpm --dir frontend typecheck
pnpm --dir frontend lint
pnpm --dir frontend build
```

Expected: all commands exit 0 before feature code changes.

### Task 2: Session Navigation

**Files:**
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`

- [ ] **Step 1: Write failing tests**

Add tests that click real status filter controls and assert:

```typescript
expect(client.listChatSessions).toHaveBeenCalledWith(projectId, {
  limit: 20,
  status: 'failed',
})
expect(screen.queryByText('Archived')).toBeNull()
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
pnpm --dir frontend test -- App.test.tsx -t "session navigation"
```

Expected: tests fail because the status filters and left navigation do not
exist.

- [ ] **Step 3: Implement minimal navigation**

Add `historyStatusFilter` state, pass it to `refreshHistory`, render all,
running, succeeded and failed filters, and keep archive absent.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
pnpm --dir frontend test -- App.test.tsx -t "session navigation"
```

Expected: targeted tests pass.

### Task 3: Context and Usage Panel

**Files:**
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`

- [ ] **Step 1: Write failing tests**

Add tests that select a session and assert selected-session provider usage,
known cost, tokens, latency and unknown values render from
`ChatSessionDetailResponse.provider_usage`.

- [ ] **Step 2: Verify RED**

Run targeted tests and confirm failure because context cards do not exist.

- [ ] **Step 3: Implement minimal context panel**

Render a right panel from selected session detail. Do not invent missing values.

- [ ] **Step 4: Verify GREEN**

Run targeted tests and confirm pass.

### Task 4: Minimap and Action Stepper

**Files:**
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`

- [ ] **Step 1: Write failing minimap tests**

Assert one minimap item per persisted message and that activating a minimap item
moves focus to the message region.

- [ ] **Step 2: Write failing stepper tests**

Assert tool calls, retrieval runs, retrieved chunks and provider usage render as
read-only action steps with status, latency, ranks, scores, tokens and costs.

- [ ] **Step 3: Verify RED**

Run targeted tests and confirm they fail for missing UI.

- [ ] **Step 4: Implement minimap and stepper**

Use selected session detail only. Do not call chat or retrieval APIs.

- [ ] **Step 5: Verify GREEN**

Run targeted tests and confirm pass.

### Task 5: Source Viewer

**Files:**
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`

- [ ] **Step 1: Write failing source viewer tests**

Click a citation with `source_id`, assert `getSource(projectId, sourceId)` is
called, source metadata renders, and lookup failure keeps citation metadata
visible with an isolated error.

- [ ] **Step 2: Verify RED**

Run targeted tests and confirm failure because the viewer does not exist.

- [ ] **Step 3: Implement source viewer**

Add selected citation/source state, call `getSource` only with a source id, and
isolate loading/error state.

- [ ] **Step 4: Verify GREEN**

Run targeted tests and confirm pass.

### Task 6: STT and Memory Decisions

**Files:**
- Modify or create backend/frontend files only after documentation check.
- Modify: `docs/roadmap.md`
- Modify: `docs/progress.md`

- [ ] **Step 1: Fetch Qwen/DashScope STT docs**

Run Context7 CLI `library` then `docs` for the current Qwen/DashScope STT API.
If Context7 cannot provide docs or quota fails, do not implement Qwen STT from
memory.

- [ ] **Step 2: Choose implementation path**

If Qwen docs and backend contract are feasible, write backend tests first. If
not, implement browser speech recognition fallback with unsupported/error
states and document Qwen STT as deferred.

- [ ] **Step 3: Memory decision**

Search for existing durable preference/memory contracts. If none exist, update
docs to defer memory and do not render fake UI.

### Task 7: Final Verification

**Files:**
- Modify: `openspec/changes/m36-chat-functional-workspace/tasks.md`
- Modify: `docs/progress.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Run full frontend gate**

```powershell
pnpm --dir frontend test
pnpm --dir frontend typecheck
pnpm --dir frontend lint
pnpm --dir frontend build
```

- [ ] **Step 2: Run OpenSpec and diff hygiene**

```powershell
npx --yes @fission-ai/openspec validate m36-chat-functional-workspace --strict
npx --yes @fission-ai/openspec validate --specs --strict --no-interactive
git diff --check
```

- [ ] **Step 3: Run browser QA**

Start local backend/frontend or use mocked browser QA harness. Verify desktop
and mobile chat workspace, console errors, text overlap and source viewer
states.

- [ ] **Step 4: Commit and prepare PR**

Stage only intended files, commit, push and open a draft PR if validation is
clean.
