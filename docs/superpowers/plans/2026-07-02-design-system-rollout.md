# Design System Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the frontend from legacy app-wide CSS to a token-backed shadcn/Radix-ready design system, starting with Runtime Settings and then expanding by safe vertical slices.

**Architecture:** Keep `App` as the behavior owner initially, extract presentational UI in small files, expand `frontend/src/components/ui/*` only when a real migrated surface needs it, and delete related `App.css` legacy selectors as each slice lands. Each slice must preserve behavior through existing tests and add focused tests for new primitives or accessibility contracts.

**Tech Stack:** React 19, Vite 8, TypeScript 6, Tailwind CSS v4, shadcn-compatible local primitives, `class-variance-authority`, `clsx`, `tailwind-merge`, Vitest, Testing Library.

---

## File Structure

- Modify `frontend/src/components/ui/button.tsx`: keep `Button` and `IconButton` as the action contract; add variants only when a migrated surface needs them.
- Create `frontend/src/components/ui/control.tsx`: tokenized `Input`, `Textarea`, `NativeSelect`, and form-control helper wrappers.
- Create `frontend/src/components/ui/control.test.tsx`: prove labels, disabled state, class conflict handling, and stable `data-slot` markers.
- Create `frontend/src/components/ui/badge.tsx`: `Badge` and `StatusBadge` for capabilities, connection state, job state, scores, and table status.
- Create `frontend/src/components/ui/badge.test.tsx`: prove variants map to token classes and accessible text remains caller-owned.
- Create `frontend/src/components/ui/tabs.tsx`: native button-based tabs/segmented controls for existing view switchers and filters.
- Create `frontend/src/components/ui/tabs.test.tsx`: prove `aria-pressed`/active state and disabled behavior.
- Create `frontend/src/components/ui/data-list.tsx`: reusable dense list rows and row action layout.
- Create `frontend/src/components/ui/feedback.tsx`: `EmptyState`, `InlineFeedback`, and `Callout`.
- Create `frontend/src/features/runtime/RuntimeSettingsView.tsx`: presentational runtime settings panels extracted from `App.tsx`.
- Create `frontend/src/features/runtime/runtimeUi.ts`: shared runtime labels, capability helpers, option labels, and status presentation helpers that do not call the API.
- Create `frontend/src/features/runtime/RuntimeSettingsView.test.tsx`: focused presentational tests for Runtime Settings / Provider Connections.
- Modify `frontend/src/App.tsx`: keep state, effects, API calls, and handlers; delegate runtime rendering to `RuntimeSettingsView`.
- Modify `frontend/src/App.test.tsx`: keep existing behavior coverage and add assertions for accessible runtime tabs, form labels, connection check status, and destructive confirmation.
- Modify `frontend/src/App.css`: remove CSS selectors that are replaced by primitives in each slice; keep only shell layout and transitional selectors until final cleanup.

---

### Task 1: Baseline And Branch Hygiene

**Files:**
- No source changes.

- [ ] **Step 1: Start from latest main**

Run:

```powershell
git fetch origin main
git status --short --branch
```

Expected: working tree clean and current branch based on `origin/main`. If `main` is locked by another worktree, create or reuse a `codex/design-system-rollout-*` branch from the commit pointed to by `origin/main`.

- [ ] **Step 2: Run frontend baseline**

Run:

```powershell
pnpm --dir frontend test
pnpm --dir frontend typecheck
pnpm --dir frontend lint
pnpm --dir frontend build
```

Expected: all commands exit `0`. If this fails before changes, stop and record the failing command before editing.

- [ ] **Step 3: Inspect CSS debt before editing**

Run:

```powershell
rg -n "#[0-9a-fA-F]{3,8}|rgba\(|linear-gradient|radial-gradient|box-shadow" frontend/src/App.css frontend/src/index.css
rg -n "^\\.[a-zA-Z0-9_-]+|^:is|^\\[data-theme|^@media|^:root" frontend/src/App.css
```

Expected: output confirms the current hardcoded color and selector debt. Use this as the before state for the rollout PR description.

- [ ] **Step 4: Commit nothing**

Do not commit in this task. It is a baseline and orientation gate only.

---

### Task 2: Add Missing Control Primitives

**Files:**
- Create: `frontend/src/components/ui/control.tsx`
- Create: `frontend/src/components/ui/control.test.tsx`
- Modify: `frontend/src/components/ui/button-variants.ts` only if a control needs a matching action size.

- [ ] **Step 1: Write failing control tests**

Create `frontend/src/components/ui/control.test.tsx`:

```tsx
/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'

import { Input, NativeSelect, Textarea } from './control'

function classTokens(element: Element): string[] {
  return element.className.split(/\s+/).filter(Boolean)
}

afterEach(() => {
  cleanup()
})

describe('control primitives', () => {
  test('Input uses tokenized control classes and a stable slot', () => {
    render(<Input aria-label="Connection id" className="h-12" />)

    const input = screen.getByRole('textbox', { name: 'Connection id' })
    const tokens = classTokens(input)
    expect(input.getAttribute('data-slot')).toBe('input')
    expect(tokens).toContain('border-input')
    expect(tokens).toContain('bg-background')
    expect(tokens).toContain('h-12')
    expect(tokens).not.toContain('h-9')
  })

  test('Textarea keeps the caller label and stable slot', () => {
    render(<Textarea aria-label="Prompt" />)

    const textarea = screen.getByRole('textbox', { name: 'Prompt' })
    expect(textarea.getAttribute('data-slot')).toBe('textarea')
  })

  test('NativeSelect exposes combobox semantics and stable slot', () => {
    render(
      <NativeSelect aria-label="Connection">
        <option value="">Select connection</option>
        <option value="qwen-hosted">Qwen hosted</option>
      </NativeSelect>,
    )

    const select = screen.getByRole('combobox', { name: 'Connection' })
    expect(select.getAttribute('data-slot')).toBe('native-select')
  })
})
```

- [ ] **Step 2: Run the failing test**

Run:

```powershell
pnpm --dir frontend test src/components/ui/control.test.tsx
```

Expected: FAIL because `frontend/src/components/ui/control.tsx` does not exist.

- [ ] **Step 3: Implement controls**

Create `frontend/src/components/ui/control.tsx`:

```tsx
import {
  type InputHTMLAttributes,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
  forwardRef,
} from 'react'

import { cn } from '@/lib/utils'

const controlClassName = [
  'w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground',
  'transition-colors placeholder:text-muted-foreground',
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
  'focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50',
].join(' ')

export type InputProps = InputHTMLAttributes<HTMLInputElement>

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', ...props }, ref) => (
    <input
      className={cn('h-9', controlClassName, className)}
      data-slot="input"
      ref={ref}
      type={type}
      {...props}
    />
  ),
)
Input.displayName = 'Input'

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <textarea
      className={cn('min-h-24 resize-y', controlClassName, className)}
      data-slot="textarea"
      ref={ref}
      {...props}
    />
  ),
)
Textarea.displayName = 'Textarea'

export type NativeSelectProps = SelectHTMLAttributes<HTMLSelectElement>

export const NativeSelect = forwardRef<HTMLSelectElement, NativeSelectProps>(
  ({ className, ...props }, ref) => (
    <select
      className={cn('h-9', controlClassName, className)}
      data-slot="native-select"
      ref={ref}
      {...props}
    />
  ),
)
NativeSelect.displayName = 'NativeSelect'
```

- [ ] **Step 4: Verify controls**

Run:

```powershell
pnpm --dir frontend test src/components/ui/control.test.tsx
pnpm --dir frontend typecheck
```

Expected: both commands pass.

- [ ] **Step 5: Commit controls**

Run:

```powershell
git add frontend/src/components/ui/control.tsx frontend/src/components/ui/control.test.tsx
git commit -m "feat(frontend): add form control primitives"
```

---

### Task 3: Add Feedback, Badge, Tabs, And Data List Primitives

**Files:**
- Create: `frontend/src/components/ui/badge.tsx`
- Create: `frontend/src/components/ui/badge.test.tsx`
- Create: `frontend/src/components/ui/tabs.tsx`
- Create: `frontend/src/components/ui/tabs.test.tsx`
- Create: `frontend/src/components/ui/data-list.tsx`
- Create: `frontend/src/components/ui/feedback.tsx`

- [ ] **Step 1: Write badge tests**

Create `frontend/src/components/ui/badge.test.tsx`:

```tsx
/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'

import { Badge, StatusBadge } from './badge'

afterEach(() => {
  cleanup()
})

describe('Badge', () => {
  test('renders neutral badge with stable slot', () => {
    render(<Badge>chat</Badge>)

    const badge = screen.getByText('chat')
    expect(badge.getAttribute('data-slot')).toBe('badge')
    expect(badge.className).toContain('border-border')
  })

  test('renders destructive status badge through tokens', () => {
    render(<StatusBadge tone="danger">failed</StatusBadge>)

    const badge = screen.getByText('failed')
    expect(badge.getAttribute('data-tone')).toBe('danger')
    expect(badge.className).toContain('text-destructive')
  })
})
```

- [ ] **Step 2: Write tabs tests**

Create `frontend/src/components/ui/tabs.test.tsx`:

```tsx
/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'

import { SegmentedControl, SegmentedControlItem } from './tabs'

afterEach(() => {
  cleanup()
})

describe('SegmentedControl', () => {
  test('marks active item with aria-pressed', () => {
    render(
      <SegmentedControl aria-label="Runtime sections">
        <SegmentedControlItem active>Connections</SegmentedControlItem>
        <SegmentedControlItem>Model catalog</SegmentedControlItem>
      </SegmentedControl>,
    )

    expect(
      screen.getByRole('button', { name: 'Connections' }).getAttribute('aria-pressed'),
    ).toBe('true')
    expect(
      screen.getByRole('button', { name: 'Model catalog' }).getAttribute('aria-pressed'),
    ).toBe('false')
  })
})
```

- [ ] **Step 3: Run failing primitive tests**

Run:

```powershell
pnpm --dir frontend test src/components/ui/badge.test.tsx src/components/ui/tabs.test.tsx
```

Expected: FAIL because `badge.tsx` and `tabs.tsx` do not exist.

- [ ] **Step 4: Implement badge primitive**

Create `frontend/src/components/ui/badge.tsx`:

```tsx
import { type HTMLAttributes, forwardRef } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium leading-5',
  {
    defaultVariants: {
      tone: 'neutral',
    },
    variants: {
      tone: {
        danger: 'border-destructive/30 bg-destructive/10 text-destructive',
        neutral: 'border-border bg-muted text-muted-foreground',
        primary: 'border-primary/20 bg-primary/10 text-foreground',
        success: 'border-primary/20 bg-primary/10 text-foreground',
        warning: 'border-border bg-accent text-accent-foreground',
      },
    },
  },
)

export type BadgeProps = HTMLAttributes<HTMLSpanElement> &
  VariantProps<typeof badgeVariants>

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, tone, ...props }, ref) => (
    <span
      className={cn(badgeVariants({ tone }), className)}
      data-slot="badge"
      ref={ref}
      {...props}
    />
  ),
)
Badge.displayName = 'Badge'

export type StatusBadgeProps = BadgeProps

export const StatusBadge = forwardRef<HTMLSpanElement, StatusBadgeProps>(
  ({ tone = 'neutral', ...props }, ref) => (
    <Badge data-tone={tone ?? 'neutral'} ref={ref} tone={tone} {...props} />
  ),
)
StatusBadge.displayName = 'StatusBadge'
```

- [ ] **Step 5: Implement tabs primitive**

Create `frontend/src/components/ui/tabs.tsx`:

```tsx
import { type ButtonHTMLAttributes, type HTMLAttributes, forwardRef } from 'react'

import { cn } from '@/lib/utils'

export type SegmentedControlProps = HTMLAttributes<HTMLDivElement>

export const SegmentedControl = forwardRef<HTMLDivElement, SegmentedControlProps>(
  ({ className, ...props }, ref) => (
    <div
      className={cn('inline-flex items-center gap-1 rounded-md border border-border bg-muted p-1', className)}
      data-slot="segmented-control"
      ref={ref}
      {...props}
    />
  ),
)
SegmentedControl.displayName = 'SegmentedControl'

export type SegmentedControlItemProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  active?: boolean
}

export const SegmentedControlItem = forwardRef<
  HTMLButtonElement,
  SegmentedControlItemProps
>(({ active = false, className, type = 'button', ...props }, ref) => (
  <button
    aria-pressed={active}
    className={cn(
      'inline-flex h-8 items-center rounded-sm px-3 text-sm font-medium text-muted-foreground transition-colors',
      'hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
      'disabled:pointer-events-none disabled:opacity-50',
      active && 'bg-background text-foreground shadow-sm',
      className,
    )}
    data-active={active ? '' : undefined}
    data-slot="segmented-control-item"
    ref={ref}
    type={type}
    {...props}
  />
))
SegmentedControlItem.displayName = 'SegmentedControlItem'
```

- [ ] **Step 6: Implement data list and feedback primitives**

Create `frontend/src/components/ui/data-list.tsx`:

```tsx
import { type HTMLAttributes, forwardRef } from 'react'

import { cn } from '@/lib/utils'

export const DataList = forwardRef<HTMLUListElement, HTMLAttributes<HTMLUListElement>>(
  ({ className, ...props }, ref) => (
    <ul className={cn('grid gap-2', className)} data-slot="data-list" ref={ref} {...props} />
  ),
)
DataList.displayName = 'DataList'

export const DataListItem = forwardRef<HTMLLIElement, HTMLAttributes<HTMLLIElement>>(
  ({ className, ...props }, ref) => (
    <li
      className={cn('rounded-md border border-border bg-card p-3 text-card-foreground', className)}
      data-slot="data-list-item"
      ref={ref}
      {...props}
    />
  ),
)
DataListItem.displayName = 'DataListItem'

export const DataListItemActions = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div className={cn('flex flex-wrap items-center gap-2', className)} data-slot="data-list-item-actions" ref={ref} {...props} />
  ),
)
DataListItemActions.displayName = 'DataListItemActions'
```

Create `frontend/src/components/ui/feedback.tsx`:

```tsx
import { type HTMLAttributes, forwardRef } from 'react'

import { cn } from '@/lib/utils'

export const EmptyState = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      className={cn('rounded-md border border-dashed border-border bg-muted/40 p-4 text-sm text-muted-foreground', className)}
      data-slot="empty-state"
      ref={ref}
      {...props}
    />
  ),
)
EmptyState.displayName = 'EmptyState'

export type InlineFeedbackProps = HTMLAttributes<HTMLParagraphElement> & {
  tone?: 'danger' | 'neutral' | 'success'
}

export const InlineFeedback = forwardRef<HTMLParagraphElement, InlineFeedbackProps>(
  ({ className, role, tone = 'neutral', ...props }, ref) => (
    <p
      className={cn(
        'text-sm',
        tone === 'danger' && 'font-medium text-destructive',
        tone === 'neutral' && 'text-muted-foreground',
        tone === 'success' && 'font-medium text-foreground',
        className,
      )}
      data-slot="inline-feedback"
      data-tone={tone}
      ref={ref}
      role={role ?? (tone === 'danger' ? 'alert' : undefined)}
      {...props}
    />
  ),
)
InlineFeedback.displayName = 'InlineFeedback'

export type CalloutProps = HTMLAttributes<HTMLDivElement> & {
  tone?: 'danger' | 'neutral' | 'success'
}

export const Callout = forwardRef<HTMLDivElement, CalloutProps>(
  ({ className, role, tone = 'neutral', ...props }, ref) => (
    <div
      className={cn(
        'rounded-md border p-3 text-sm',
        tone === 'danger' && 'border-destructive/30 bg-destructive/10 text-destructive',
        tone === 'neutral' && 'border-border bg-muted/50 text-muted-foreground',
        tone === 'success' && 'border-primary/20 bg-primary/10 text-foreground',
        className,
      )}
      data-slot="callout"
      data-tone={tone}
      ref={ref}
      role={role ?? (tone === 'danger' ? 'alert' : undefined)}
      {...props}
    />
  ),
)
Callout.displayName = 'Callout'
```

- [ ] **Step 7: Verify primitives**

Run:

```powershell
pnpm --dir frontend test src/components/ui/badge.test.tsx src/components/ui/tabs.test.tsx
pnpm --dir frontend typecheck
pnpm --dir frontend lint
```

Expected: all commands pass.

- [ ] **Step 8: Commit primitives**

Run:

```powershell
git add frontend/src/components/ui/badge.tsx frontend/src/components/ui/badge.test.tsx frontend/src/components/ui/tabs.tsx frontend/src/components/ui/tabs.test.tsx frontend/src/components/ui/data-list.tsx frontend/src/components/ui/feedback.tsx
git commit -m "feat(frontend): add rollout ui primitives"
```

---

### Task 4: Runtime Settings Presentational Extraction

**Files:**
- Create: `frontend/src/features/runtime/runtimeUi.ts`
- Create: `frontend/src/features/runtime/RuntimeSettingsView.tsx`
- Create: `frontend/src/features/runtime/RuntimeSettingsView.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Move pure runtime helpers**

Create `frontend/src/features/runtime/runtimeUi.ts` with pure helpers copied from `App.tsx`:

```ts
import { type ProviderConnection, type ProviderModel } from '@/lib/apiClient'

export function connectionsForCapability(
  connections: ProviderConnection[],
  capability: string,
): ProviderConnection[] {
  return connections.filter((connection) => connection.capabilities.includes(capability))
}

export function connectionOptionLabel(connection: ProviderConnection): string {
  const label = metadataLabel(connection.metadata)
  if (label === null) {
    return `${connection.connection_id} (${connection.provider}/${connection.connection_type})`
  }
  return `${label} (${connection.provider}/${connection.connection_type})`
}

export function metadataLabel(metadata: Record<string, unknown> | null): string | null {
  const label = metadata?.label
  return typeof label === 'string' && label.trim().length > 0 ? label.trim() : null
}

export function providerModelOptions({
  capability,
  connectionId,
  providerModels,
}: {
  capability: string
  connectionId: string
  providerModels: ProviderModel[]
}): ProviderModel[] {
  const trimmedConnectionId = connectionId.trim()
  if (trimmedConnectionId.length === 0) {
    return []
  }
  return providerModels.filter(
    (model) =>
      model.connection_id === trimmedConnectionId &&
      model.capabilities.includes(capability),
  )
}
```

Remove the duplicated helper bodies from `App.tsx` only after imports compile.

- [ ] **Step 2: Create runtime presentational component shell**

Create `frontend/src/features/runtime/RuntimeSettingsView.tsx` and move these components from `App.tsx` into it without changing labels or behavior:

- `RuntimeSettingsPanel`
- `RuntimeConnectionsPanel`
- `CapabilitySelector`
- `RuntimeModelCatalogPanel`
- `RuntimeGlobalDefaultsPanel`
- `RuntimeProjectOverridesPanel`
- `ConnectionSecretSummary`
- `ConnectionCheckSummary`
- `ConnectionSelect`
- `ProviderModelSelect`
- `ProviderModelCatalogView`
- `RuntimeSlotList`
- `ProjectRuntimeSettingsView`

Keep props explicit. Import UI primitives from:

```tsx
import { Button } from '@/components/ui/button'
import { Badge, StatusBadge } from '@/components/ui/badge'
import { Input, NativeSelect } from '@/components/ui/control'
import { DataList, DataListItem, DataListItemActions } from '@/components/ui/data-list'
import { EmptyState, InlineFeedback } from '@/components/ui/feedback'
import { Field, FieldControl, FieldError, FieldHelp, FieldLabel } from '@/components/ui/field'
import { Panel, PanelBody, PanelDescription, PanelHeader, PanelTitle } from '@/components/ui/panel'
import { SegmentedControl, SegmentedControlItem } from '@/components/ui/tabs'
```

- [ ] **Step 3: Update `App.tsx` imports and usage**

In `frontend/src/App.tsx`, replace local runtime component definitions with:

```tsx
import { RuntimeSettingsPanel } from '@/features/runtime/RuntimeSettingsView'
```

Keep all runtime state, effects, API calls, and submit handlers in `App`.

- [ ] **Step 4: Add focused runtime presentational tests**

Create `frontend/src/features/runtime/RuntimeSettingsView.test.tsx` with tests that render `RuntimeSettingsPanel` using minimal fixtures and assert:

- Runtime submodule buttons are exposed as buttons and active item uses `aria-pressed="true"`.
- Connection form fields are label-addressable: `Provider`, `Connection type`, `Base URL`, `Secret connection`, `Capabilities`.
- Connection check result text renders after passing `connectionCheckResults`.
- Delete confirmation requires the exact connection id label text.

- [ ] **Step 5: Run focused runtime tests**

Run:

```powershell
pnpm --dir frontend test src/features/runtime/RuntimeSettingsView.test.tsx src/App.test.tsx
pnpm --dir frontend typecheck
```

Expected: all commands pass.

- [ ] **Step 6: Commit runtime extraction**

Run:

```powershell
git add frontend/src/features/runtime frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "refactor(frontend): extract runtime settings view"
```

---

### Task 5: Runtime Settings Visual Migration

**Files:**
- Modify: `frontend/src/features/runtime/RuntimeSettingsView.tsx`
- Modify: `frontend/src/features/runtime/RuntimeSettingsView.test.tsx`
- Modify: `frontend/src/App.css`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Replace runtime forms with primitives**

In `RuntimeSettingsView.tsx`, replace runtime-specific `<label className="field">`, raw `input`, raw `select`, and form feedback nodes with `Field`, `FieldLabel`, `FieldControl`, `FieldHelp`, `FieldError`, `Input`, `NativeSelect`, and `InlineFeedback`. Preserve existing visible labels exactly.

- [ ] **Step 2: Replace connection rows with data-list primitives**

In `RuntimeSettingsView.tsx`, replace `authoring-row`, `connection-row`, `authoring-row-actions`, and connection delete confirmation wrappers with `DataList`, `DataListItem`, `DataListItemActions`, `Button`, `Badge`, `StatusBadge`, `EmptyState`, and `InlineFeedback`.

- [ ] **Step 3: Replace runtime submodule nav with segmented controls**

Use `SegmentedControl` and `SegmentedControlItem` for runtime submodule navigation. Active item must keep `aria-pressed="true"`.

- [ ] **Step 4: Delete replaced CSS**

In `frontend/src/App.css`, remove selectors whose only remaining purpose was runtime forms and provider connections:

- `.runtime-grid`
- `.runtime-panel`
- `.runtime-section`
- `.runtime-form-grid`
- `.runtime-field-wide`
- `.project-runtime-grid`
- `.capability-*` after `CapabilitySelector` is migrated
- `.connection-*` after connection rows and checks are migrated

Keep layout selectors only if still referenced by another non-runtime surface.

- [ ] **Step 5: Run runtime tests**

Run:

```powershell
pnpm --dir frontend test src/features/runtime/RuntimeSettingsView.test.tsx src/App.test.tsx
pnpm --dir frontend typecheck
pnpm --dir frontend lint
```

Expected: all commands pass.

- [ ] **Step 6: Browser QA runtime slice**

Run:

```powershell
pnpm --dir frontend dev -- --host 127.0.0.1
```

Verify in the browser:

- `/settings/runtime` renders Connections, Model catalog, Global defaults, and Project overrides.
- Connection rows, destructive confirmation, check connection result, capability tokens, selects, empty states, and form errors are readable in light, dark, and purple themes.
- Mobile width near `390px` stacks forms without overlapping text.
- Console has no errors.

Stop the dev server after QA.

- [ ] **Step 7: Commit runtime visual slice**

Run:

```powershell
git add frontend/src/features/runtime frontend/src/App.css frontend/src/App.test.tsx
git commit -m "feat(frontend): migrate runtime settings styling"
```

---

### Task 6: Authoring And Ingestion Slice

**Files:**
- Create: `frontend/src/features/authoring/AuthoringView.tsx`
- Create: `frontend/src/features/authoring/AuthoringView.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Extract presentational authoring components**

Move these local components from `App.tsx` to `AuthoringView.tsx`:

- `AuthoringPanel`
- `ProjectAccessPanel`
- `UserAccessLists`
- `KnowledgeReviewPanel`
- `SourceList`
- `IngestionJobsPanel`
- `IngestionJobList`

Keep state and API handlers in `App.tsx`.

- [ ] **Step 2: Apply primitives**

Use `Panel`, `Field`, `Input`, `NativeSelect`, `Textarea`, `Button`, `DataList`, `DataListItem`, `Badge`, `EmptyState`, and `InlineFeedback`. Preserve button names and form labels.

- [ ] **Step 3: Delete replaced CSS**

Remove authoring-specific selectors from `App.css` after the extracted component no longer references them:

- `.authoring-grid`
- `.authoring-panel`
- `.authoring-form`
- `.source-form-grid`
- `.authoring-list`
- `.authoring-row`
- `.authoring-row-actions`
- `.access-list-grid`
- `.knowledge-proposal-*`
- `.ingestion-*`
- `.job-*`

- [ ] **Step 4: Verify authoring**

Run:

```powershell
pnpm --dir frontend test src/features/authoring/AuthoringView.test.tsx src/App.test.tsx
pnpm --dir frontend typecheck
pnpm --dir frontend lint
```

Expected: all commands pass.

- [ ] **Step 5: Browser QA authoring**

Verify Projects, Users, Knowledge, Sources, and ingestion job states in desktop and mobile. Confirm forms retain labels and destructive/retry actions stay clear.

- [ ] **Step 6: Commit authoring slice**

Run:

```powershell
git add frontend/src/features/authoring frontend/src/App.tsx frontend/src/App.css frontend/src/App.test.tsx
git commit -m "feat(frontend): migrate authoring styling"
```

---

### Task 7: Observability Slice

**Files:**
- Create: `frontend/src/components/ui/table.tsx`
- Create: `frontend/src/features/observability/ObservabilityView.tsx`
- Create: `frontend/src/features/observability/ObservabilityView.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`

- [ ] **Step 1: Add table primitive if needed**

Create `frontend/src/components/ui/table.tsx` with `TableScroll`, `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, and `TableCell` wrappers using tokenized classes.

- [ ] **Step 2: Extract observability presentational components**

Move these components from `App.tsx` to `ObservabilityView.tsx`:

- `ObservabilityPanel`
- `ObservabilityContent`
- `ObservabilitySummaryContent`
- `ObservabilitySummaryMetrics`
- `ObservabilityCostsContent`
- `ObservabilityErrorsContent`
- `ObservabilityLatencyContent`
- `ObservabilityBreakdowns`
- `StatusBreakdown`
- `ErrorMessages`
- `ProviderUsageTable`
- `ProviderLatencyTable`
- `SessionHealth`
- `BreakdownHeader`
- `MetricCard`

- [ ] **Step 3: Apply primitives**

Use `Panel`, `Badge`, `StatusBadge`, `SegmentedControl`, `DataList`, `Table`, `EmptyState`, and tokenized text classes. Preserve metric values and table headers.

- [ ] **Step 4: Delete replaced CSS**

Remove observability selectors from `App.css` that are no longer referenced:

- `.observability-*`
- `.metric-grid`
- `.metric-card`
- `.breakdown-*`
- `.status-breakdown-list`
- `.observability-table`
- `.table-scroll`

- [ ] **Step 5: Verify observability**

Run:

```powershell
pnpm --dir frontend test src/features/observability/ObservabilityView.test.tsx src/App.test.tsx
pnpm --dir frontend typecheck
pnpm --dir frontend lint
```

Expected: all commands pass.

- [ ] **Step 6: Browser QA observability**

Verify Summary, Costs, Errors, and Latency tabs across light, dark, purple, desktop, and mobile. Confirm tables scroll horizontally instead of overflowing.

- [ ] **Step 7: Commit observability slice**

Run:

```powershell
git add frontend/src/components/ui/table.tsx frontend/src/features/observability frontend/src/App.tsx frontend/src/App.css
git commit -m "feat(frontend): migrate observability styling"
```

---

### Task 8: Chat, History, And Inspector Slice

**Files:**
- Create: `frontend/src/features/chat/ChatWorkspaceView.tsx`
- Create: `frontend/src/features/chat/ChatWorkspaceView.test.tsx`
- Create: `frontend/src/features/history/HistoryInspectorView.tsx`
- Create: `frontend/src/features/history/HistoryInspectorView.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`
- Modify: `frontend/src/components/ChatPipelineSteps.tsx`
- Modify: `frontend/src/components/ChatPipelineSteps.test.tsx`

- [ ] **Step 1: Extract chat presentational components**

Move chat presentational components from `App.tsx` to `ChatWorkspaceView.tsx`, including `SpeechInputControl`, `ResponsePanel`, `ResponseContent`, `QuestionPrompt`, `ResponseDetailsPanel`, `ResponseDetailsContent`, `ResponseUsageStrip`, and `KnowledgeDraftCard`. Keep streaming state and submit handlers in `App.tsx`.

- [ ] **Step 2: Extract history and inspector components**

Move `SessionNavigationPanel`, `WorkspaceInspectorPanel`, `ConversationMinimap`, `SessionContextPanel`, `InternalActionStepper`, `SessionDetailPanel`, and detail renderers to `HistoryInspectorView.tsx`.

- [ ] **Step 3: Apply primitives carefully**

Use primitives for cards, buttons, data lists, badges, feedback, and tabs. Preserve sticky prompt behavior, transcript scroll behavior, inline/overlay inspector behavior, and focusable message articles.

- [ ] **Step 4: Update ChatPipelineSteps**

Replace legacy wrapper classes in `ChatPipelineSteps.tsx` with tokenized classes for the ticker, summary button, step rows, status markers, detail chips, and expanded details. Keep existing semantics of `details`, `summary`, and step rows.

- [ ] **Step 5: Delete replaced CSS**

Remove migrated chat/history selectors from `App.css`, including response, pipeline, session, minimap, detail, retrieved chunk, source viewer, and inspector selectors that are no longer referenced.

- [ ] **Step 6: Verify chat and history**

Run:

```powershell
pnpm --dir frontend test src/features/chat/ChatWorkspaceView.test.tsx src/features/history/HistoryInspectorView.test.tsx src/components/ChatPipelineSteps.test.tsx src/App.test.tsx
pnpm --dir frontend typecheck
pnpm --dir frontend lint
```

Expected: all commands pass.

- [ ] **Step 7: Browser QA chat**

Verify chat submit, streaming status, response details, source viewer, session rail, inspector inline and overlay behavior, desktop, mobile, light, dark, and purple.

- [ ] **Step 8: Commit chat/history slice**

Run:

```powershell
git add frontend/src/features/chat frontend/src/features/history frontend/src/components/ChatPipelineSteps.tsx frontend/src/components/ChatPipelineSteps.test.tsx frontend/src/App.tsx frontend/src/App.css
git commit -m "feat(frontend): migrate chat history styling"
```

---

### Task 9: Final CSS Cleanup And Full Verification

**Files:**
- Modify: `frontend/src/App.css`
- Modify: `frontend/src/index.css`
- Modify: migrated feature files only if final verification exposes concrete issues.

- [ ] **Step 1: Find remaining hardcoded visual debt**

Run:

```powershell
rg -n "#[0-9a-fA-F]{3,8}|rgba\(|linear-gradient|radial-gradient|box-shadow" frontend/src/App.css frontend/src/index.css
rg -n "\\.field|\\.panel|\\.secondary-button|\\.danger-button|\\.authoring-|\\.runtime-|\\.observability-|\\.message-card|\\.session-" frontend/src/App.css frontend/src/App.tsx frontend/src/features frontend/src/components
```

Expected: `index.css` may still contain token definitions. `App.css` should contain shell layout and transitional responsive rules only. Any remaining hardcoded colors in `App.css` must be either removed or justified as a token candidate.

- [ ] **Step 2: Move missing tokens to `index.css`**

If a repeated visual value remains, add a semantic token to `frontend/src/index.css` instead of keeping the value in feature CSS. Use existing token naming style and update `@theme inline` only for tokens that Tailwind utilities need.

- [ ] **Step 3: Run full frontend gate**

Run:

```powershell
pnpm --dir frontend test
pnpm --dir frontend typecheck
pnpm --dir frontend lint
pnpm --dir frontend build
```

Expected: all commands pass.

- [ ] **Step 4: Run final browser QA**

Run:

```powershell
pnpm --dir frontend dev -- --host 127.0.0.1
```

Verify:

- Chat, Account Appearance, Settings Authoring, Settings Observability, Settings Runtime.
- Desktop and mobile near `390px`.
- Light, dark, purple.
- Sidebar open/closed.
- No overlapping text, no unreadable buttons, no horizontal document overflow except intentional table scroll.
- Console clean.

Stop the dev server after QA.

- [ ] **Step 5: Commit cleanup**

Run:

```powershell
git add frontend/src/App.css frontend/src/index.css frontend/src/features frontend/src/components frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "chore(frontend): clean up legacy design css"
```

---

## Execution Recommendation

Use Subagent-Driven execution. Dispatch one subagent per task or per slice, review the diff after each task, and only continue when the current slice has tests, typecheck, lint, build, and browser QA evidence.

The first implementation PR should stop after Task 5. That creates the missing primitives and migrates Runtime Settings / Provider Connections as the reference slice. Later PRs should continue from Task 6 onward.
