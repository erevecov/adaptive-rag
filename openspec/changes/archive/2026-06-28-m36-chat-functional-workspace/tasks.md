# Tasks M36 functional chat workspace

## 1. Setup

- [x] 1.1 Fetch `origin/main` and create branch/worktree
  `codex/chat-functional-workspace`.
- [x] 1.2 Confirm no active OpenSpec changes exist.
- [x] 1.3 Install frontend dependencies and run baseline frontend tests,
  typecheck, lint and build.
- [x] 1.4 Add OpenSpec proposal, design, tasks and spec deltas.

## 2. Session navigation

- [x] 2.1 Add failing tests for status-filtered session navigation.
- [x] 2.2 Implement left session navigation using `listChatSessions` status
  filters and real counts from session summaries.
- [x] 2.3 Verify targeted frontend tests.

## 3. Context and usage panel

- [x] 3.1 Add failing tests for selected-session usage/cost/token/latency
  summaries.
- [x] 3.2 Implement context panel from session detail and observability data.
- [x] 3.3 Verify targeted frontend tests.

## 4. Conversation minimap

- [x] 4.1 Add failing tests for message minimap navigation.
- [x] 4.2 Implement minimap from persisted messages.
- [x] 4.3 Verify targeted frontend tests.

## 5. Internal action stepper

- [x] 5.1 Add failing tests for tool/retrieval/provider stepper rendering.
- [x] 5.2 Implement read-only action stepper from chat audit detail.
- [x] 5.3 Verify targeted frontend tests.

## 6. Source and citation viewer

- [x] 6.1 Add failing tests for citation source lookup and failure isolation.
- [x] 6.2 Implement source viewer using `getSource` when citation metadata has
  `source_id`.
- [x] 6.3 Verify targeted frontend tests.

## 7. STT and memory decisions

- [x] 7.1 Fetch current Qwen/DashScope STT documentation before any Qwen-backed
  implementation.
- [x] 7.2 Implement only a verified STT path: backend Qwen contract with tests,
  or browser fallback with unsupported/error states and Qwen deferred.
- [x] 7.3 Implement memory only with durable verified storage, otherwise
  document it as deferred.

## 8. Final validation and docs

- [x] 8.1 Run full frontend test, typecheck, lint and build.
- [x] 8.2 Run OpenSpec strict validation and `git diff --check`.
- [x] 8.3 Run browser QA for desktop and mobile chat workspace views.
- [x] 8.4 Update progress/roadmap docs and prepare PR.

## 9. UI/UX fidelity pass

- [x] 9.1 Compare the rendered chat workspace against reference
  captures.
- [x] 9.2 Reorganize chat into a functional three-zone workspace: session rail,
  central chat and right inspector tabs.
- [x] 9.3 Verify inspector tab interactions, minimap navigation and source
  viewer focus behavior with targeted tests.
- [x] 9.4 Capture desktop and mobile screenshots and check for horizontal
  overflow.

## 10. Global appearance settings

- [x] 10.1 Inspect app-wide theme helpers and appearance settings behavior.
- [x] 10.2 Add failing tests for the Settings module, global theme application
  and persisted theme hydration.
- [x] 10.3 Implement Light, Dark and Purple themes through global
  `data-theme`, `.dark` and `localStorage` helpers.
- [x] 10.4 Browser-QA all workspace tabs under all three themes on desktop and
  mobile, including horizontal overflow checks.
