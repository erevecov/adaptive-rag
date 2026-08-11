# Beautiful UI Square Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild all 19 Beautiful UI patterns as typed Adaptive RAG components and use them across the existing frontend wherever product semantics match, under one global square Grok Build visual contract.

**Architecture:** Keep `components/ui` as the low-level accessible foundation and add `components/beautiful-ui` as a presentational pattern layer. Existing feature views continue to own API calls, permissions, mutations and domain state; they translate domain data into pattern props. Migrate shared foundations first, create and test the complete catalog second, then integrate disjoint feature surfaces in parallel before one integrated verification pass.

**Tech Stack:** React 19, TypeScript 6, Tailwind CSS 4, Radix UI, Lucide React, Vitest, Testing Library, Vite.

## Global Constraints

- Rebuild all 19 patterns; do not store or paste literal demo copies.
- Do not add `glimm`, `liveline`, unavailable private atoms, or another runtime dependency.
- Preserve Light, Dark and Purple themes.
- Use a global `2px` radius for panels, controls, menus, tables, chips, cards and overlays.
- Reserve circular styling for genuinely circular content such as avatars, status dots and circular progress marks.
- Preserve current routes, API contracts, authorization, state ownership and mutations.
- Pattern components must not import `ApiClient`, call `fetch`, persist domain records, inspect authorization or invent optimistic success.
- Keep the existing `680px` mobile breakpoint and 44px narrow-viewport touch targets.
- Respect `prefers-reduced-motion` for every new animation.
- Use test-first RED/GREEN cycles for each task; a new test must fail for the intended missing behavior before production code is written.
- Do not create Storybook, a showcase route or a parallel demo application.

---

## File Structure

### Shared foundation

- Modify `frontend/src/index.css`: global square radius and pattern animation tokens.
- Modify `frontend/src/App.css`: remove the chat-only square probe after global adoption.
- Modify `frontend/src/components/ui/{button-variants,control,panel,select,table,tabs,dropdown-menu,popover,data-list,feedback,nav}.tsx`: square, flat shared chrome.
- Modify the matching `frontend/src/components/ui/*.test.tsx` files: behavioral and rendered-class protection.

### Pattern catalog

Create one production file per adapted source pattern under
`frontend/src/components/beautiful-ui/`:

- `loading-grid.tsx`
- `reasoning-trace.tsx`
- `streaming-answer.tsx`
- `approval-prompt.tsx`
- `tool-activity.tsx`
- `agent-task-list.tsx`
- `chat-surface.tsx`
- `prompt-composer.tsx`
- `recommendation-panel.tsx`
- `context-chunk-list.tsx`
- `change-table.tsx`
- `records-grid.tsx`
- `filtered-task-table.tsx`
- `workspace-navigation.tsx`
- `command-search.tsx`
- `insight-deck.tsx`
- `code-stream.tsx`
- `parameter-tuner.tsx`
- `selection-toolbar.tsx`
- `index.ts`
- `README.md`

Tests are grouped by behavior rather than mirrored one-file-per-component:

- `activity-patterns.test.tsx`
- `conversation-patterns.test.tsx`
- `decision-patterns.test.tsx`
- `data-patterns.test.tsx`

### Feature adoption

- Shell/history: `frontend/src/features/shell/AppShell.tsx`, `frontend/src/features/history/HistoryInspectorView.tsx` and tests.
- Chat/retrieval: `frontend/src/features/chat/ChatWorkspaceView.tsx`, `frontend/src/components/ChatPipelineSteps.tsx`, `frontend/src/components/MarkdownAnswer.tsx`, `frontend/src/features/retrieval/RetrievalPlaygroundView.tsx` and tests.
- Authoring: `frontend/src/features/authoring/AuthoringView.tsx` and test.
- Observability/runtime: `frontend/src/features/observability/ObservabilityView.tsx`, `frontend/src/features/runtime/RuntimeSettingsView.tsx` and tests.
- App integration: `frontend/src/App.tsx`, `frontend/src/App.test.tsx` only where the feature boundaries require wiring changes.

---

### Task 1: Global Square Foundation

**Files:**

- Modify: `frontend/src/index.css`
- Modify: `frontend/src/App.css`
- Modify: `frontend/src/components/ui/button-variants.ts`
- Modify: `frontend/src/components/ui/control.tsx`
- Modify: `frontend/src/components/ui/panel.tsx`
- Modify: `frontend/src/components/ui/select.tsx`
- Modify: `frontend/src/components/ui/table.tsx`
- Modify: `frontend/src/components/ui/tabs.tsx`
- Modify: `frontend/src/components/ui/dropdown-menu.tsx`
- Modify: `frontend/src/components/ui/popover.tsx`
- Modify: `frontend/src/components/ui/data-list.tsx`
- Modify: `frontend/src/components/ui/feedback.tsx`
- Modify: `frontend/src/components/ui/nav.tsx`
- Test: matching files in `frontend/src/components/ui/*.test.tsx`

**Interfaces:**

- Consumes: existing semantic theme variables and public primitive props.
- Produces: the unchanged primitive APIs with global `rounded-[2px]` chrome and no chat-only square scope.

- [ ] **Step 1: Install the locked frontend dependencies**

Run: `cd frontend && pnpm install --frozen-lockfile`

Expected: pnpm exits 0 without changing `package.json` or `pnpm-lock.yaml`.

- [ ] **Step 2: Add failing square-contract tests**

Update the primitive tests to assert rendered behavior rather than source text. Representative assertions:

```tsx
render(<Button>Save</Button>)
expect(screen.getByRole('button', { name: 'Save' }).className).toContain(
  'rounded-[2px]',
)

render(<Panel>Content</Panel>)
expect(screen.getByText('Content').closest('[data-slot="panel"]')?.className)
  .toContain('rounded-[2px]')

render(<Input aria-label="Name" />)
expect(screen.getByRole('textbox', { name: 'Name' }).className).toContain(
  'rounded-[2px]',
)
```

- [ ] **Step 3: Run the focused tests to verify RED**

Run: `cd frontend && pnpm test -- src/components/ui`

Expected: FAIL because primitives still render `rounded-md`/`rounded-lg`.

- [ ] **Step 4: Implement the global square contract**

Set the base radius and Tailwind aliases in `index.css`:

```css
:root {
  --radius: 2px;
}

@theme inline {
  --radius-sm: 2px;
  --radius-md: 2px;
  --radius-lg: 2px;
}
```

Replace fixed non-circular radius utilities in the listed primitives with
`rounded-[2px]`. Remove the entire `data-chat-radius='square'` override block
from `index.css` and its obsolete explanatory comment. Keep `rounded-full` only
where the element is visually circular.

- [ ] **Step 5: Run focused tests and refactor while green**

Run: `cd frontend && pnpm test -- src/components/ui`

Expected: PASS. Then run `pnpm typecheck` and keep it green while removing only
radius overrides made redundant by this task.

- [ ] **Step 6: Commit the foundation**

```bash
git add frontend/src/index.css frontend/src/App.css frontend/src/components/ui
git commit -m "feat(ui): apply global square visual foundation"
```

---

### Task 2: Activity And Execution Patterns

**Files:**

- Create: `frontend/src/components/beautiful-ui/loading-grid.tsx`
- Create: `frontend/src/components/beautiful-ui/reasoning-trace.tsx`
- Create: `frontend/src/components/beautiful-ui/tool-activity.tsx`
- Create: `frontend/src/components/beautiful-ui/agent-task-list.tsx`
- Create: `frontend/src/components/beautiful-ui/code-stream.tsx`
- Create: `frontend/src/components/beautiful-ui/activity-patterns.test.tsx`

**Interfaces:**

```ts
export type LoadingGridProps = {
  label: string
  elapsedMs?: number | null
  variant?: 'grid' | 'dots' | 'orbit'
}

export type TraceStep = {
  detail?: ReactNode
  elapsedMs?: number | null
  id: string
  label: string
  status: 'running' | 'completed' | 'failed'
}
export type ReasoningTraceProps = {
  defaultExpanded?: boolean
  label: string
  steps: readonly TraceStep[]
}

export type ToolActivityItem = {
  detail?: ReactNode
  id: string
  label: string
  meta?: string
  status: 'running' | 'completed' | 'failed'
}
export type ToolActivityProps = {
  items: readonly ToolActivityItem[]
  label: string
}

export type AgentTaskItem = {
  detail?: ReactNode
  id: string
  label: string
  meta?: string
  status: 'running' | 'completed' | 'failed'
}
export type AgentTaskListProps = {
  emptyLabel: string
  label: string
  tasks: readonly AgentTaskItem[]
}

export type CodeStreamProps = {
  code: string
  copyLabel: string
  filename?: string
  language?: string
  onCopy?(code: string): void | Promise<void>
}
```

- [ ] **Step 1: Write failing real-component tests**

```tsx
test('reasoning trace exposes expansion state and failed step detail', async () => {
  const user = userEvent.setup()
  render(
    <ReasoningTrace
      label="Chat steps"
      steps={[{ id: 'retrieval', label: 'Retrieval', status: 'failed', detail: 'Timed out' }]}
    />,
  )
  const toggle = screen.getByRole('button', { name: /Chat steps/ })
  expect(toggle).toHaveAttribute('aria-expanded', 'false')
  await user.click(toggle)
  expect(toggle).toHaveAttribute('aria-expanded', 'true')
  expect(screen.getByText('Timed out')).toBeVisible()
})

test('code stream copies the exact code through its callback', async () => {
  const onCopy = vi.fn()
  render(<CodeStream code={'const answer = 42'} copyLabel="Copy code" onCopy={onCopy} />)
  await userEvent.click(screen.getByRole('button', { name: 'Copy code' }))
  expect(onCopy).toHaveBeenCalledWith('const answer = 42')
})
```

Also cover `LoadingGrid` status semantics, empty `AgentTaskList`, completed and
failed states, and independent expansion of `ToolActivity` rows.

- [ ] **Step 2: Run tests to verify RED**

Run: `cd frontend && pnpm test -- src/components/beautiful-ui/activity-patterns.test.tsx`

Expected: FAIL because the five modules do not exist.

- [ ] **Step 3: Implement the five controlled components**

Use `Button`, `IconButton`, `EmptyState`, `StatusBadge` and `cn`. Use CSS
animations only under `motion-safe:` utilities. Do not add internal timers
except the elapsed label derived from the supplied `elapsedMs`.

- [ ] **Step 4: Run GREEN and refactor**

Run: `cd frontend && pnpm test -- src/components/beautiful-ui/activity-patterns.test.tsx`

Expected: PASS with no console warnings. Run `pnpm typecheck` before commit.

- [ ] **Step 5: Commit activity patterns**

```bash
git add frontend/src/components/beautiful-ui
git commit -m "feat(ui): add activity and execution patterns"
```

---

### Task 3: Conversation Patterns

**Files:**

- Create: `frontend/src/components/beautiful-ui/streaming-answer.tsx`
- Create: `frontend/src/components/beautiful-ui/chat-surface.tsx`
- Create: `frontend/src/components/beautiful-ui/prompt-composer.tsx`
- Create: `frontend/src/components/beautiful-ui/context-chunk-list.tsx`
- Create: `frontend/src/components/beautiful-ui/conversation-patterns.test.tsx`

**Interfaces:**

```ts
export type StreamingAnswerProps = {
  actions?: ReactNode
  children: ReactNode
  isStreaming?: boolean
  sources?: ReactNode
}

export type ChatSurfaceProps = {
  composer: ReactNode
  empty?: ReactNode
  isEmpty?: boolean
  transcript: ReactNode
}

export type PromptComposerProps = {
  attachments?: ReactNode
  busy?: boolean
  canSubmit?: boolean
  children?: ReactNode
  onCancel?(): void
  onSubmit(event: FormEvent<HTMLFormElement>): void
  prompt: string
  promptLabel: string
  submitLabel: string
  onPromptChange(value: string): void
  tools?: ReactNode
}

export type ContextChunkItem = {
  content: ReactNode
  id: string
  meta?: ReactNode
  sourceLabel: string
}
export type ContextChunkListProps = {
  chunks: readonly ContextChunkItem[]
  emptyLabel: string
  label: string
  onOpenChunk?(id: string): void
}
```

- [ ] **Step 1: Write failing conversation tests**

```tsx
test('prompt composer submits through a labelled form and cancels while busy', async () => {
  const onSubmit = vi.fn((event: React.FormEvent) => event.preventDefault())
  const onCancel = vi.fn()
  render(
    <PromptComposer
      busy
      canSubmit={false}
      onCancel={onCancel}
      onPromptChange={() => undefined}
      onSubmit={onSubmit}
      prompt="Question"
      promptLabel="Ask"
      submitLabel="Send"
    />,
  )
  expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  await userEvent.click(screen.getByRole('button', { name: 'Cancel request' }))
  expect(onCancel).toHaveBeenCalledTimes(1)
})

test('context chunk list opens the selected real chunk id', async () => {
  const onOpenChunk = vi.fn()
  render(
    <ContextChunkList
      chunks={[{ id: 'chunk-7', content: 'Evidence', sourceLabel: 'Guide.pdf' }]}
      emptyLabel="No context"
      label="Retrieved context"
      onOpenChunk={onOpenChunk}
    />,
  )
  await userEvent.click(screen.getByRole('button', { name: /Guide.pdf/ }))
  expect(onOpenChunk).toHaveBeenCalledWith('chunk-7')
})
```

Cover empty `ChatSurface`, streaming `aria-busy`, source/action slots and
controlled prompt changes.

- [ ] **Step 2: Run tests to verify RED**

Run: `cd frontend && pnpm test -- src/components/beautiful-ui/conversation-patterns.test.tsx`

Expected: FAIL because the four modules do not exist.

- [ ] **Step 3: Implement conversation components**

Compose existing UI primitives. `PromptComposer` renders the form and textarea
but accepts attachments/tools as slots so feature-owned file and speech logic
stays outside. `ChatSurface` must keep transcript and composer scrollers
separate.

- [ ] **Step 4: Run GREEN and commit**

Run: `cd frontend && pnpm test -- src/components/beautiful-ui/conversation-patterns.test.tsx && pnpm typecheck`

```bash
git add frontend/src/components/beautiful-ui
git commit -m "feat(ui): add conversation patterns"
```

---

### Task 4: Decision Patterns

**Files:**

- Create: `frontend/src/components/beautiful-ui/approval-prompt.tsx`
- Create: `frontend/src/components/beautiful-ui/recommendation-panel.tsx`
- Create: `frontend/src/components/beautiful-ui/change-table.tsx`
- Create: `frontend/src/components/beautiful-ui/selection-toolbar.tsx`
- Create: `frontend/src/components/beautiful-ui/decision-patterns.test.tsx`

**Interfaces:**

```ts
export type ApprovalChoice = { id: string; label: string }
export type ApprovalPromptProps = {
  busy?: boolean
  choices: readonly ApprovalChoice[]
  customLabel?: string
  onChoose(id: string): void
  onCustomSubmit?(value: string): void
  question: string
}

export type RecommendationAlternative = {
  description?: ReactNode
  id: string
  label: string
}
export type RecommendationPanelProps = {
  alternatives?: readonly RecommendationAlternative[]
  confidence?: number | null
  description: ReactNode
  onAccept(): void
  onAlternative?(id: string): void
  title: string
}

export type ChangeTableRow = {
  field: string
  id: string
  original: ReactNode
  proposed: ReactNode
}
export type ChangeTableProps = { label: string; rows: readonly ChangeTableRow[] }

export type SelectionAction = { id: string; label: string }
export type SelectionToolbarProps = {
  actions: readonly SelectionAction[]
  disabled?: boolean
  onAction(id: string): void
}
```

- [ ] **Step 1: Write failing choice and callback tests**

```tsx
test('approval prompt emits only the chosen id', async () => {
  const onChoose = vi.fn()
  render(
    <ApprovalPrompt
      choices={[{ id: 'approve', label: 'Approve' }, { id: 'reject', label: 'Reject' }]}
      onChoose={onChoose}
      question="Review proposal"
    />,
  )
  await userEvent.click(screen.getByRole('button', { name: 'Approve' }))
  expect(onChoose).toHaveBeenCalledWith('approve')
})

test('selection toolbar stays generic and emits a semantic action id', async () => {
  const onAction = vi.fn()
  render(
    <SelectionToolbar
      actions={[{ id: 'explain', label: 'Explain' }]}
      onAction={onAction}
    />,
  )
  await userEvent.click(screen.getByRole('button', { name: 'Explain' }))
  expect(onAction).toHaveBeenCalledWith('explain')
})
```

Cover confidence bounds, missing confidence, custom answer trimming and semantic
table headers.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && pnpm test -- src/components/beautiful-ui/decision-patterns.test.tsx`

Expected: FAIL because the four modules do not exist.

- [ ] **Step 3: Implement controlled decision patterns**

Clamp displayed confidence to `0..100` without fabricating a default. Disable
choices when `busy`. Keep `SelectionToolbar` unmounted from features during
this change; only its library contract and tests ship.

- [ ] **Step 4: Run GREEN and commit**

Run: `cd frontend && pnpm test -- src/components/beautiful-ui/decision-patterns.test.tsx && pnpm typecheck`

```bash
git add frontend/src/components/beautiful-ui
git commit -m "feat(ui): add decision patterns"
```

---

### Task 5: Data, Navigation And Insight Patterns

**Files:**

- Create: `frontend/src/components/beautiful-ui/records-grid.tsx`
- Create: `frontend/src/components/beautiful-ui/filtered-task-table.tsx`
- Create: `frontend/src/components/beautiful-ui/workspace-navigation.tsx`
- Create: `frontend/src/components/beautiful-ui/command-search.tsx`
- Create: `frontend/src/components/beautiful-ui/insight-deck.tsx`
- Create: `frontend/src/components/beautiful-ui/parameter-tuner.tsx`
- Create: `frontend/src/components/beautiful-ui/data-patterns.test.tsx`
- Create: `frontend/src/components/beautiful-ui/index.ts`
- Create: `frontend/src/components/beautiful-ui/README.md`

**Interfaces:**

```ts
export type RecordsGridColumn<Row> = {
  header: string
  id: string
  render(row: Row): ReactNode
  sortValue?(row: Row): string | number
}
export type RecordsGridProps<Row extends { id: string }> = {
  columns: readonly RecordsGridColumn<Row>[]
  emptyLabel: string
  label: string
  rows: readonly Row[]
}

export type FilterOption = { id: string; label: string }
export type FilteredTaskTableProps<Row extends { id: string }> = {
  activeFilter: string
  columns: readonly RecordsGridColumn<Row>[]
  emptyLabel: string
  filters: readonly FilterOption[]
  label: string
  onFilterChange(id: string): void
  rows: readonly Row[]
}

export type WorkspaceNavigationItem = {
  active?: boolean
  badge?: string | number
  id: string
  label: string
}
export type WorkspaceNavigationSection = {
  id: string
  items: readonly WorkspaceNavigationItem[]
  label: string
}
export type WorkspaceNavigationProps = {
  label: string
  onNavigate(id: string): void
  sections: readonly WorkspaceNavigationSection[]
}

export type CommandSearchItem = { id: string; label: string; meta?: string }
export type CommandSearchProps = {
  emptyLabel: string
  items: readonly CommandSearchItem[]
  label: string
  onSelect(id: string): void
  placeholder: string
}

export type InsightItem = {
  body: ReactNode
  id: string
  title: string
  trend?: readonly InsightPoint[]
}
export type InsightPoint = { x: number; y: number }
export type InsightDeckProps = { insights: readonly InsightItem[]; label: string }

export type ParameterDefinition = {
  id: string
  label: string
  max: number
  min: number
  step?: number
  value: number
}
export type ParameterTunerProps = {
  label: string
  onChange(id: string, value: number): void
  parameters: readonly ParameterDefinition[]
}
```

- [ ] **Step 1: Write failing data behavior tests**

```tsx
test('records grid sorts a sortable column without mutating input rows', async () => {
  const rows = [{ id: 'b', name: 'Beta' }, { id: 'a', name: 'Alpha' }] as const
  render(
    <RecordsGrid
      columns={[{ id: 'name', header: 'Name', render: (row) => row.name, sortValue: (row) => row.name }]}
      emptyLabel="No records"
      label="Records"
      rows={rows}
    />,
  )
  await userEvent.click(screen.getByRole('button', { name: /Name/ }))
  expect(screen.getAllByRole('row')[1]).toHaveTextContent('Alpha')
  expect(rows[0].name).toBe('Beta')
})

test('command search filters case-insensitively and emits the selected id', async () => {
  const onSelect = vi.fn()
  render(
    <CommandSearch
      emptyLabel="No matches"
      items={[{ id: 's-1', label: 'Architecture Guide' }]}
      label="Search sources"
      onSelect={onSelect}
      placeholder="Search"
    />,
  )
  await userEvent.type(screen.getByRole('searchbox'), 'architecture')
  await userEvent.click(screen.getByRole('button', { name: /Architecture Guide/ }))
  expect(onSelect).toHaveBeenCalledWith('s-1')
})
```

Cover filter callbacks, `aria-current`, insight paging boundaries, a trend SVG
whose accessible label comes from its insight title, empty states and numeric
tuner clamping.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && pnpm test -- src/components/beautiful-ui/data-patterns.test.tsx`

Expected: FAIL because the six modules do not exist.

- [ ] **Step 3: Implement data and navigation patterns**

Use real table semantics in `RecordsGrid`. Keep filtering and sorting local
presentation state; callbacks communicate product selection. Render compact
insight trends as a dependency-free SVG only when `trend` contains at least two
caller-supplied points; do not add `liveline` or a demo series.

- [ ] **Step 4: Export all 19 components and document provenance**

`index.ts` exports the component and public prop types from every catalog file.
`README.md` records the source URL, inspection date `2026-08-11`, original name,
internal name, removed dependency and adoption status. Mark only
`SelectionToolbar` as `adapted-reserved`; all others are `adapted-adopted` once
Tasks 6-9 complete.

- [ ] **Step 5: Run GREEN, typecheck and catalog mutation check**

Run: `cd frontend && pnpm test -- src/components/beautiful-ui && pnpm typecheck`

Expected: all four catalog test files pass and every export resolves.

- [ ] **Step 6: Commit the complete catalog**

```bash
git add frontend/src/components/beautiful-ui
git commit -m "feat(ui): complete adapted Beautiful UI catalog"
```

---

### Task 6: Shell And History Adoption

**Files:**

- Modify: `frontend/src/features/shell/AppShell.tsx`
- Modify: `frontend/src/features/shell/AppShell.test.tsx`
- Modify: `frontend/src/features/history/HistoryInspectorView.tsx`
- Modify: `frontend/src/features/history/HistoryInspectorView.test.tsx`

**Interfaces:**

- Consumes: `WorkspaceNavigation`, `CommandSearch`, `LoadingGrid`,
  `ContextChunkList`, `ReasoningTrace`, `RecordsGrid`.
- Produces: unchanged exported shell/history props and callbacks.

- [ ] **Step 1: Add failing feature-adoption tests**

Render real `AppSidebar`, `SessionNavigationPanel` and inspector components.
Assert user-visible behavior plus pattern slots:

```tsx
expect(screen.getByRole('navigation', { name: 'Primary Navigation' }))
  .toHaveAttribute('data-slot', 'workspace-navigation')
expect(
  screen.getByRole('searchbox', { name: 'Search sessions' })
    .closest('[data-slot="command-search"]'),
).toBeTruthy()
expect(screen.getByRole('list', { name: 'Retrieved context' }))
  .toHaveAttribute('data-slot', 'context-chunk-list')
```

Keep existing rename, archive, Escape, focus-trap and source-opening assertions.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && pnpm test -- src/features/shell/AppShell.test.tsx src/features/history/HistoryInspectorView.test.tsx`

Expected: FAIL because the current views do not render the new pattern slots.

- [ ] **Step 3: Replace presentation with pattern composition**

Map current navigation arrays into `WorkspaceNavigation`. Add `CommandSearch`
only to lists long enough to benefit; do not remove existing session filters.
Replace inspector loading skeletons with `LoadingGrid`, context lists with
`ContextChunkList`, and internal action steps with `ReasoningTrace`. Preserve
overlay and mobile logic exactly.

- [ ] **Step 4: Run GREEN and commit**

Run: `cd frontend && pnpm test -- src/features/shell/AppShell.test.tsx src/features/history/HistoryInspectorView.test.tsx && pnpm typecheck`

```bash
git add frontend/src/features/shell frontend/src/features/history
git commit -m "feat(ui): adopt square patterns in shell and history"
```

---

### Task 7: Chat And Retrieval Adoption

**Files:**

- Modify: `frontend/src/features/chat/ChatWorkspaceView.tsx`
- Modify: `frontend/src/features/chat/ChatWorkspaceView.test.tsx`
- Modify: `frontend/src/components/ChatPipelineSteps.tsx`
- Modify: `frontend/src/components/ChatPipelineSteps.test.tsx`
- Modify: `frontend/src/components/MarkdownAnswer.tsx`
- Modify: `frontend/src/components/MarkdownAnswer.test.tsx`
- Modify: `frontend/src/features/retrieval/RetrievalPlaygroundView.tsx`
- Modify: `frontend/src/features/retrieval/RetrievalPlaygroundView.test.tsx`

**Interfaces:**

- Consumes: `ChatSurface`, `PromptComposer`, `StreamingAnswer`,
  `ReasoningTrace`, `ToolActivity`, `ContextChunkList`, `CodeStream`,
  `LoadingGrid`.
- Produces: unchanged `ChatWorkspacePanelProps`, chat callbacks, streaming
  handling, attachments, speech behavior and retrieval submit contract.

- [ ] **Step 1: Add failing adoption tests without mocking catalog components**

Extend existing tests:

```tsx
expect(screen.getByRole('region', { name: 'Chat Workspace' }))
  .toHaveAttribute('data-slot', 'chat-surface')
expect(screen.getByRole('form', { name: 'Chat composer' }))
  .toHaveAttribute('data-slot', 'prompt-composer')
expect(screen.getByRole('region', { name: 'Chat Pipeline Steps' }))
  .toHaveAttribute('data-slot', 'reasoning-trace')
```

Add a Markdown code-fence test that clicks the actual `CodeStream` copy button
and asserts the supplied code. Keep existing send/cancel, attachments, SSE
step, source, retry, regenerate and question-edit tests.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && pnpm test -- src/features/chat/ChatWorkspaceView.test.tsx src/components/ChatPipelineSteps.test.tsx src/components/MarkdownAnswer.test.tsx src/features/retrieval/RetrievalPlaygroundView.test.tsx`

Expected: FAIL because the new pattern slots are absent.

- [ ] **Step 3: Adopt conversation and activity patterns**

Wrap the current transcript/composer in `ChatSurface` and `PromptComposer`
without moving feature-owned handlers. Refactor `ChatPipelineSteps` to render
`ReasoningTrace`. Use `StreamingAnswer` around assistant content,
`ToolActivity` for tool details, `ContextChunkList` for retrieved evidence and
`CodeStream` for fenced code. Use `LoadingGrid` for retrieval loading without
replacing error/empty feedback.

- [ ] **Step 4: Run GREEN and commit**

Run: `cd frontend && pnpm test -- src/features/chat/ChatWorkspaceView.test.tsx src/components/ChatPipelineSteps.test.tsx src/components/MarkdownAnswer.test.tsx src/features/retrieval/RetrievalPlaygroundView.test.tsx && pnpm typecheck`

```bash
git add frontend/src/features/chat frontend/src/features/retrieval frontend/src/components/ChatPipelineSteps.tsx frontend/src/components/ChatPipelineSteps.test.tsx frontend/src/components/MarkdownAnswer.tsx frontend/src/components/MarkdownAnswer.test.tsx
git commit -m "feat(ui): adopt square patterns in chat and retrieval"
```

---

### Task 8: Authoring Adoption

**Files:**

- Modify: `frontend/src/features/authoring/AuthoringView.tsx`
- Modify: `frontend/src/features/authoring/AuthoringView.test.tsx`

**Interfaces:**

- Consumes: `ApprovalPrompt`, `RecommendationPanel`, `ChangeTable`,
  `AgentTaskList`, `FilteredTaskTable`, `RecordsGrid`, `CommandSearch`,
  `LoadingGrid`.
- Produces: unchanged `AuthoringPanel` props and existing create, delete,
  ingest, retry, approve, refine and reject callbacks.

- [ ] **Step 1: Add failing real-flow adoption tests**

```tsx
expect(screen.getByRole('article', { name: /Knowledge Proposal/ }))
  .toHaveAttribute('data-slot', 'recommendation-panel')
expect(screen.getByRole('region', { name: 'Ingestion Jobs' }))
  .toHaveAttribute('data-slot', 'agent-task-list')
```

Preserve existing assertions that reject stays gated without a reason, binary
source uploads expose state, retries target the correct job and destructive
actions identify the correct record.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && pnpm test -- src/features/authoring/AuthoringView.test.tsx`

Expected: FAIL because current lists do not expose the new pattern contracts.

- [ ] **Step 3: Map existing domain flows to patterns**

Use `RecordsGrid` for data-dense workspaces/users/sources where it improves
scanability; keep compact lists where actions require card layout. Use
`RecommendationPanel` plus `ApprovalPrompt` for actual proposal lifecycle
actions and `ChangeTable` only when both original and proposed values exist.
Use `AgentTaskList`/`FilteredTaskTable` for ingestion jobs and `LoadingGrid` for
active loads.

- [ ] **Step 4: Run GREEN and commit**

Run: `cd frontend && pnpm test -- src/features/authoring/AuthoringView.test.tsx && pnpm typecheck`

```bash
git add frontend/src/features/authoring
git commit -m "feat(ui): adopt square patterns in authoring"
```

---

### Task 9: Observability And Runtime Adoption

**Files:**

- Modify: `frontend/src/features/observability/ObservabilityView.tsx`
- Modify: `frontend/src/features/observability/ObservabilityView.test.tsx`
- Modify: `frontend/src/features/runtime/RuntimeSettingsView.tsx`
- Modify: `frontend/src/features/runtime/RuntimeSettingsView.test.tsx`

**Interfaces:**

- Consumes: `InsightDeck`, `RecordsGrid`, `FilteredTaskTable`,
  `ParameterTuner`, `LoadingGrid`, `RecommendationPanel`.
- Produces: unchanged observability filters and runtime connection, model,
  default and workspace-override callbacks.

- [ ] **Step 1: Add failing metric and runtime adoption tests**

```tsx
expect(screen.getByRole('region', { name: 'Operational insights' }))
  .toHaveAttribute('data-slot', 'insight-deck')
expect(screen.getByRole('group', { name: 'Chat retrieval parameters' }))
  .toHaveAttribute('data-slot', 'parameter-tuner')
```

Keep existing tests for tabular numerals, labelled metrics, stale refresh
warnings, provider-secret redaction, exact delete confirmation and slot saves.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && pnpm test -- src/features/observability/ObservabilityView.test.tsx src/features/runtime/RuntimeSettingsView.test.tsx`

Expected: FAIL because `InsightDeck` and `ParameterTuner` are not adopted.

- [ ] **Step 3: Adopt data and tuning patterns**

Build `InsightDeck` entries only from actual summary metrics. Use
`RecordsGrid` for provider usage, latency, connections and model catalogs.
Use `ParameterTuner` only for existing bounded numeric retrieval controls; keep
model/provider selects as existing Radix selects. Replace loading skeleton
collections with `LoadingGrid` while preserving stale data and error banners.

- [ ] **Step 4: Run GREEN and commit**

Run: `cd frontend && pnpm test -- src/features/observability/ObservabilityView.test.tsx src/features/runtime/RuntimeSettingsView.test.tsx && pnpm typecheck`

```bash
git add frontend/src/features/observability frontend/src/features/runtime
git commit -m "feat(ui): adopt square patterns in operations settings"
```

---

### Task 10: Integration, Catalog Reconciliation And Full Verification

**Files:**

- Modify: `frontend/src/components/beautiful-ui/README.md`

**Interfaces:**

- Consumes: all feature exports and the complete catalog barrel.
- Produces: one integrated app with the same external behavior, 19 exported
  adapted components, 18 currently adopted patterns and one reserved pattern.

- [ ] **Step 1: Reconcile catalog status**

Update `README.md` so every adopted component lists its real consumer files and
`SelectionToolbar` remains `adapted-reserved`. If the full suite exposes
missing data or callback wiring, return that fix to Tasks 6-9 and preserve the
existing `App` request orchestration.

- [ ] **Step 2: Run the full frontend verification**

Run in `frontend/`:

```bash
pnpm test
pnpm lint
pnpm typecheck
pnpm build
```

Expected: all commands exit 0 with no failed tests or TypeScript errors.

- [ ] **Step 3: Run repository-scope checks**

From the repository root:

```bash
git diff --check 90818e70..HEAD
git status --short
```

Run:

```bash
openspec list
openspec validate --all --strict --no-interactive
```

Expected: `openspec list` reports no active change for this visual-only work,
and strict validation passes for every existing canonical spec.

- [ ] **Step 4: Perform visual E2E review**

Start the Vite app and inspect desktop and mobile widths in Light, Dark and
Purple. Exercise:

- sidebar open/closed and contextual navigation;
- session search/filter and inspector overlay;
- empty, loading, error and populated chat states;
- pinned composer, attachment controls and response details;
- authoring proposals and ingestion jobs;
- retrieval result context;
- observability insights/tables;
- runtime parameter controls, menus and destructive confirmation;
- horizontal table scroll, focus rings, Escape handling and reduced motion.

Record concrete screenshots or DOM evidence for each theme/width combination.

- [ ] **Step 5: Run a final diff review and commit**

Verify every changed line traces to the approved redesign, no demo nouns or
dependencies were introduced, and unrelated user changes remain untouched.

```bash
git add frontend docs/superpowers/plans/2026-08-11-beautiful-ui-square-frontend-redesign.md
git commit -m "feat(ui): complete square frontend redesign"
```
