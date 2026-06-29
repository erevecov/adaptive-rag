# Runtime Navigation Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the always-visible chat session sidebar with contextual navigation and split Runtime settings into clear submodules with specific actions.

**Architecture:** Keep the app in the existing React/Vite single-page structure, but separate primary navigation from secondary navigation state. The left sidebar remains the shared shell and renders either chat sessions, account modules, or a settings tree. Runtime keeps the existing API contracts and is split into four render panels: connections, model catalog, global defaults, and project overrides.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, CSS modules via `App.css`, OpenSpec.

---

## File Structure

- Modify: `openspec/specs/chat-frontend/spec.md`
  - Add scenarios for contextual sidebar navigation and Runtime submodules.
- Create: `openspec/changes/runtime-navigation-clarity/proposal.md`
  - Explain the frontend information architecture change.
- Create: `openspec/changes/runtime-navigation-clarity/design.md`
  - Point to the approved design and summarize boundaries.
- Create: `openspec/changes/runtime-navigation-clarity/tasks.md`
  - Track contract, frontend implementation, CSS, and validation.
- Create: `openspec/changes/runtime-navigation-clarity/specs/chat-frontend/spec.md`
  - Delta for contextual sidebar and Runtime submodules.
- Modify: `frontend/src/App.test.tsx`
  - Replace the old settings-tabs expectations with contextual sidebar tests.
  - Update Runtime tests to navigate to specific submodules.
- Modify: `frontend/src/App.tsx`
  - Replace overloaded `activeView` with explicit primary and submodule state.
  - Render contextual sidebar bodies.
  - Route account/settings content from sidebar selections.
  - Split Runtime render content into submodule panels.
- Modify: `frontend/src/App.css`
  - Style contextual sidebar groups, nested items, disabled account modules, and focused settings shells.
- Modify: `docs/progress.md`
  - Mention the active OpenSpec change during implementation closeout.
- Modify: `docs/roadmap.md`
  - Add the new frontend information architecture slice after M38 when implementation closes.

---

### Task 1: Add OpenSpec Contract for Contextual Sidebar and Runtime Submodules

**Files:**
- Create: `openspec/changes/runtime-navigation-clarity/proposal.md`
- Create: `openspec/changes/runtime-navigation-clarity/design.md`
- Create: `openspec/changes/runtime-navigation-clarity/tasks.md`
- Create: `openspec/changes/runtime-navigation-clarity/specs/chat-frontend/spec.md`
- Modify after implementation: `openspec/specs/chat-frontend/spec.md`

- [ ] **Step 1: Create the OpenSpec proposal**

Create `openspec/changes/runtime-navigation-clarity/proposal.md`:

```markdown
# Runtime Navigation Clarity

## Why

The current frontend can select `Settings` while the left sidebar still shows
chat sessions. Runtime settings also combine provider connections, model sync,
global defaults and project overrides behind one generic `Refresh runtime`
action. This makes the product hard to understand.

## What Changes

- Make the left sidebar contextual:
  - `Chat` shows chat sessions.
  - `My account` shows account modules.
  - `Settings` shows settings modules and submodules.
- Remove internal Settings tabs as the main navigation mechanism.
- Split Runtime into `Connections`, `Model catalog`, `Global defaults` and
  `Project overrides`.
- Replace the generic `Refresh runtime` action with submodule-specific loading
  and actions.

## Impact

- Frontend behavior and tests change.
- Existing provider runtime API contracts remain unchanged.
- Runtime safety guarantees remain unchanged: no secrets rendered, hosted and
  local connections can coexist, slots stay fixed, chat has one default model,
  and projects keep overrides over global defaults.
```

- [ ] **Step 2: Create the OpenSpec design**

Create `openspec/changes/runtime-navigation-clarity/design.md`:

```markdown
# Runtime Navigation Clarity Design

This change implements the approved design in
`docs/superpowers/specs/2026-06-29-runtime-navigation-design.md`.

## Decisions

- Keep one product shell.
- Keep `Chat`, `My account` and `Settings` as primary sidebar navigation.
- Render secondary navigation inside the sidebar based on the selected primary
  view.
- Use explicit state for selected account module, settings module and settings
  submodule.
- Keep backend runtime contracts unchanged.
- Split the Runtime UI into named panels that reuse existing handlers and API
  client calls.

## Runtime Submodules

- `Connections`: provider connection list, connection form and secret rotation.
- `Model catalog`: model sync selector/action and provider model catalog.
- `Global defaults`: fixed slots, chat model pool and global chat retrieval.
- `Project overrides`: effective project runtime settings and reset actions.

## Non-goals

- No new backend routes.
- No durable memory implementation.
- No full URL router.
- No runtime provider or slot redesign.
```

- [ ] **Step 3: Create the OpenSpec task list**

Create `openspec/changes/runtime-navigation-clarity/tasks.md`:

```markdown
# Tasks: Runtime Navigation Clarity

## 1. Contract

- [ ] 1.1 Add `chat-frontend` delta for contextual sidebar navigation.
- [ ] 1.2 Add `chat-frontend` delta for Runtime submodules.
- [ ] 1.3 Validate the OpenSpec change in strict mode.

## 2. Frontend navigation

- [ ] 2.1 Add failing sidebar tests.
- [ ] 2.2 Introduce explicit primary/module/submodule navigation state.
- [ ] 2.3 Render contextual sidebar bodies.
- [ ] 2.4 Remove Settings internal tabs from the main navigation path.

## 3. Focused settings content

- [ ] 3.1 Add Authoring submodule routing.
- [ ] 3.2 Add Observability submodule routing.
- [ ] 3.3 Add Runtime submodule routing.
- [ ] 3.4 Replace generic `Refresh runtime` with specific actions.

## 4. Verification

- [ ] 4.1 Run focused frontend tests.
- [ ] 4.2 Run frontend typecheck, lint and build.
- [ ] 4.3 Run OpenSpec strict validation.
- [ ] 4.4 Run `git diff --check`.
```

- [ ] **Step 4: Create the `chat-frontend` OpenSpec delta**

Create `openspec/changes/runtime-navigation-clarity/specs/chat-frontend/spec.md`:

```markdown
## MODIFIED Requirements

### Requirement: Frontend polish is workflow-first

The frontend MUST present the existing local product workflows as a coherent
workspace instead of a marketing landing page or a collection of disconnected
demos.

#### Scenario: Product workspace is the first screen

- **WHEN** a user opens the frontend
- **THEN** the first useful screen gives access to project context, authoring,
  ingestion, chat, history, runtime and observability workflows
- **AND** it does not require the user to pass through a marketing landing page
  before doing product work

#### Scenario: Workflow navigation preserves project context

- **WHEN** a user selects or creates a project
- **THEN** authoring, ingestion, chat, history, runtime and observability
  surfaces reuse the same project context
- **AND** changing workflow views does not silently clear valid project/source
  inputs or chat draft text

### Requirement: Frontend exposes Runtime settings without secrets

The frontend MUST expose global runtime/provider configuration and project
runtime overrides through public backend contracts without storing or rendering
provider secrets in the browser.

#### Scenario: Runtime settings are separated into named submodules

- **WHEN** a user opens Settings > Runtime
- **THEN** the UI exposes `Connections`, `Model catalog`, `Global defaults`
  and `Project overrides` as separate Runtime submodules
- **AND** each submodule renders only the controls and data for that concern
- **AND** the UI does not render a generic `Refresh runtime` button

#### Scenario: User manages global provider connections

- **WHEN** a user opens Runtime > Connections
- **THEN** the UI can list configured provider connections, readiness status
  and supported slot capabilities
- **AND** hosted and local connections can both be visible at the same time
- **AND** no plaintext API key, ciphertext or Authorization header is rendered
- **AND** creating a connection does not ask the user to type an internal
  connection ID

#### Scenario: User saves or rotates a provider secret

- **WHEN** a user enters a provider secret in Runtime > Connections
- **THEN** the frontend sends it only to the backend save/rotate endpoint
- **AND** clears the input after success or failure
- **AND** subsequent reads show only safe status such as configured time or
  non-reversible fingerprint
- **AND** the connection target is selected from existing connections

#### Scenario: User syncs the provider model catalog

- **WHEN** a user opens Runtime > Model catalog
- **THEN** the UI shows a connection selector, a `Sync models` action and the
  persisted provider model catalog
- **AND** model sync is scoped to the selected connection

#### Scenario: User configures fixed global slots

- **WHEN** a user opens Runtime > Global defaults
- **THEN** the UI presents only the fixed slots `chat`, `dense_embedding`,
  `sparse_embedding`, `rerank` and `contextualization`
- **AND** slot controls only offer compatible connections/models
- **AND** model controls are selectors populated from the persisted provider
  model catalog and current saved settings

#### Scenario: Chat pool exposes one default

- **WHEN** the global chat model pool has multiple models
- **THEN** the UI marks exactly one as default
- **AND** prevents deleting the last model or deleting the default without
  rotating it first

#### Scenario: Project runtime settings show inheritance

- **WHEN** a user opens Runtime > Project overrides
- **THEN** each slot shows whether it inherits the global default or uses a
  project override
- **AND** the UI provides a reset-to-global action for overridden slots
- **AND** project override controls do not ask for provider API keys
- **AND** project override model controls are selectors, not free-text model ID
  fields

## ADDED Requirements

### Requirement: Sidebar navigation is contextual

The frontend MUST use the left sidebar as contextual navigation for the active
primary area.

#### Scenario: Chat keeps session navigation

- **WHEN** the user selects `Chat`
- **THEN** the sidebar shows chat session creation, filters and session rows
- **AND** selecting a session still loads durable chat session detail

#### Scenario: My account shows account modules

- **WHEN** the user selects `My account`
- **THEN** the sidebar shows account modules including `Appearance`
- **AND** the sidebar does not show chat sessions
- **AND** unavailable modules such as `Memory` are clearly disabled or deferred
  unless backed by a durable contract

#### Scenario: Settings shows modules and submodules

- **WHEN** the user selects `Settings`
- **THEN** the sidebar shows `Authoring`, `Observability` and `Runtime`
- **AND** each settings module exposes its submodules in the sidebar
- **AND** the sidebar does not show chat sessions
- **AND** the main content matches the selected sidebar submodule
```

- [ ] **Step 5: Validate the OpenSpec change**

Run:

```powershell
npx --yes @fission-ai/openspec validate runtime-navigation-clarity --strict
```

Expected: command exits `0` and reports the change is valid. If it reports a formatting or scenario placement error, fix the delta before touching frontend code.

- [ ] **Step 6: Commit the contract**

Run:

```powershell
git add -- openspec/changes/runtime-navigation-clarity
git commit -m "docs: specify runtime navigation clarity"
```

Expected: one commit containing only the OpenSpec change files.

---

### Task 2: Add Failing Frontend Tests for Contextual Sidebar

**Files:**
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Replace the obsolete settings-tabs helper**

In `frontend/src/App.test.tsx`, replace:

```ts
async function openSettingsSection(
  user: { click(element: Element): Promise<void> },
  sectionName: 'Authoring' | 'Observability' | 'Runtime',
) {
  await user.click(screen.getByRole('button', { name: 'Settings' }))
  await user.click(screen.getByRole('tab', { name: sectionName }))
}
```

with:

```ts
async function openSettingsSubmodule(
  user: { click(element: Element): Promise<void> },
  moduleName: 'Authoring' | 'Observability' | 'Runtime',
  submoduleName: string,
) {
  await user.click(screen.getByRole('button', { name: 'Settings' }))
  const settingsNavigation = screen.getByRole('navigation', {
    name: 'Settings navigation',
  })
  await user.click(within(settingsNavigation).getByRole('button', { name: moduleName }))
  await user.click(
    within(settingsNavigation).getByRole('button', { name: submoduleName }),
  )
}
```

- [ ] **Step 2: Replace the old primary navigation tests**

Replace the tests named:

- `keeps primary navigation to chat, my account, and settings in the left sidebar`
- `keeps workspace tools inside settings tabs`

with:

```ts
test('keeps primary navigation stable and renders chat sessions only in Chat', async () => {
  const user = userEvent.setup()

  render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

  const sidebar = screen.getByRole('complementary', {
    name: 'Primary sidebar',
  })
  const navigation = within(sidebar).getByRole('navigation', {
    name: 'Primary navigation',
  })

  expect(
    within(navigation)
      .getAllByRole('button')
      .map((button) => button.textContent),
  ).toEqual(['Chat', 'My account', 'Settings'])
  expect(within(sidebar).getByRole('heading', { name: 'SESIONES' })).toBeTruthy()

  await user.click(within(navigation).getByRole('button', { name: 'My account' }))

  expect(within(sidebar).queryByRole('heading', { name: 'SESIONES' })).toBeNull()
  expect(
    within(sidebar).getByRole('navigation', { name: 'My account navigation' }),
  ).toBeTruthy()

  await user.click(within(navigation).getByRole('button', { name: 'Settings' }))

  expect(within(sidebar).queryByRole('heading', { name: 'SESIONES' })).toBeNull()
  expect(
    within(sidebar).getByRole('navigation', { name: 'Settings navigation' }),
  ).toBeTruthy()
})

test('shows account modules in the sidebar without rendering fake memory state', async () => {
  const user = userEvent.setup()

  render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

  await user.click(screen.getByRole('button', { name: 'My account' }))

  const accountNavigation = screen.getByRole('navigation', {
    name: 'My account navigation',
  })

  expect(
    within(accountNavigation)
      .getAllByRole('button')
      .map((button) => button.textContent),
  ).toEqual(['Appearance', 'Memory'])
  expect(
    within(accountNavigation).getByRole('button', { name: 'Memory' }),
  ).toBeDisabled()
  expect(screen.getByRole('heading', { name: 'Appearance' })).toBeTruthy()
  expect(screen.queryByText(/remembered/i)).toBeNull()
})

test('shows settings modules and submodules in the sidebar', async () => {
  const user = userEvent.setup()

  render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

  await user.click(screen.getByRole('button', { name: 'Settings' }))

  const settingsNavigation = screen.getByRole('navigation', {
    name: 'Settings navigation',
  })

  expect(within(settingsNavigation).getByRole('button', { name: 'Authoring' })).toBeTruthy()
  expect(within(settingsNavigation).getByRole('button', { name: 'Projects' })).toBeTruthy()
  expect(within(settingsNavigation).getByRole('button', { name: 'Users' })).toBeTruthy()
  expect(within(settingsNavigation).getByRole('button', { name: 'Knowledge' })).toBeTruthy()
  expect(within(settingsNavigation).getByRole('button', { name: 'Sources' })).toBeTruthy()
  expect(within(settingsNavigation).getByRole('button', { name: 'Observability' })).toBeTruthy()
  expect(within(settingsNavigation).getByRole('button', { name: 'Runtime' })).toBeTruthy()
  expect(screen.queryByRole('tablist', { name: 'Settings sections' })).toBeNull()
})
```

- [ ] **Step 3: Add focused settings submodule tests**

Add this test below the settings navigation test:

```ts
test('routes settings sidebar submodules to focused content', async () => {
  const user = userEvent.setup()

  render(<App apiClient={createClientStub({})} initialProjectId={projectId} />)

  await openSettingsSubmodule(user, 'Authoring', 'Users')
  expect(screen.getByRole('heading', { name: 'Users' })).toBeTruthy()
  expect(screen.queryByRole('heading', { name: 'Content registry' })).toBeNull()

  await openSettingsSubmodule(user, 'Authoring', 'Sources')
  expect(screen.getByRole('heading', { name: 'Content registry' })).toBeTruthy()

  await openSettingsSubmodule(user, 'Observability', 'Summary')
  expect(screen.getByRole('heading', { name: 'Summary' })).toBeTruthy()

  await openSettingsSubmodule(user, 'Runtime', 'Connections')
  expect(screen.getByRole('heading', { name: 'Connections' })).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Refresh runtime' })).toBeNull()
})
```

- [ ] **Step 4: Run the focused tests and confirm failure**

Run:

```powershell
pnpm --dir frontend test -- App.test.tsx -t "sidebar|submodules"
```

Expected: FAIL because `My account navigation`, `Settings navigation`, focused submodule routing and removal of `Refresh runtime` are not implemented yet.

- [ ] **Step 5: Commit the failing tests**

Run:

```powershell
git add -- frontend/src/App.test.tsx
git commit -m "test: define contextual sidebar navigation"
```

Expected: one commit with tests only. The commit can contain failing tests because this task is the TDD red step.

---

### Task 3: Introduce Explicit Navigation State and Contextual Sidebar Bodies

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Replace top-level navigation constants and types**

In `frontend/src/App.tsx`, replace:

```ts
const SETTINGS_SECTIONS = [
  { id: 'authoring', label: 'Authoring' },
  { id: 'observability', label: 'Observability' },
  { id: 'runtime', label: 'Runtime' },
] as const
```

with:

```ts
const SETTINGS_NAVIGATION = [
  {
    id: 'authoring',
    label: 'Authoring',
    submodules: [
      { id: 'projects', label: 'Projects' },
      { id: 'users', label: 'Users' },
      { id: 'knowledge', label: 'Knowledge' },
      { id: 'sources', label: 'Sources' },
    ],
  },
  {
    id: 'observability',
    label: 'Observability',
    submodules: [
      { id: 'summary', label: 'Summary' },
      { id: 'costs', label: 'Costs' },
      { id: 'errors', label: 'Errors' },
      { id: 'latency', label: 'Latency' },
    ],
  },
  {
    id: 'runtime',
    label: 'Runtime',
    submodules: [
      { id: 'connections', label: 'Connections' },
      { id: 'model_catalog', label: 'Model catalog' },
      { id: 'global_defaults', label: 'Global defaults' },
      { id: 'project_overrides', label: 'Project overrides' },
    ],
  },
] as const

const ACCOUNT_MODULES = [
  { id: 'appearance', label: 'Appearance', disabled: false },
  { id: 'memory', label: 'Memory', disabled: true },
] as const
```

Replace:

```ts
type SettingsSection = (typeof SETTINGS_SECTIONS)[number]['id']
type ActiveView = 'chat' | 'account' | 'settings' | SettingsSection
```

with:

```ts
type PrimaryView = 'chat' | 'account' | 'settings'
type AccountModule = (typeof ACCOUNT_MODULES)[number]['id']
type SettingsModule = (typeof SETTINGS_NAVIGATION)[number]['id']
type AuthoringSubmodule = (typeof SETTINGS_NAVIGATION)[0]['submodules'][number]['id']
type ObservabilitySubmodule =
  (typeof SETTINGS_NAVIGATION)[1]['submodules'][number]['id']
type RuntimeSubmodule = (typeof SETTINGS_NAVIGATION)[2]['submodules'][number]['id']
type SettingsSubmodule =
  | AuthoringSubmodule
  | ObservabilitySubmodule
  | RuntimeSubmodule
```

- [ ] **Step 2: Replace `activeView` state in `App`**

Replace:

```ts
const [activeView, setActiveView] = useState<ActiveView>('chat')
```

with:

```ts
const [primaryView, setPrimaryView] = useState<PrimaryView>('chat')
const [accountModule, setAccountModule] = useState<AccountModule>('appearance')
const [settingsModule, setSettingsModule] =
  useState<SettingsModule>('authoring')
const [authoringSubmodule, setAuthoringSubmodule] =
  useState<AuthoringSubmodule>('projects')
const [observabilitySubmodule, setObservabilitySubmodule] =
  useState<ObservabilitySubmodule>('summary')
const [runtimeSubmodule, setRuntimeSubmodule] =
  useState<RuntimeSubmodule>('connections')
```

Add these helpers inside `App`, near the navigation handlers:

```ts
function handlePrimaryViewChange(view: PrimaryView) {
  setPrimaryView(view)
}

function handleSettingsModuleChange(module: SettingsModule) {
  setSettingsModule(module)
  if (module === 'authoring') {
    setAuthoringSubmodule('projects')
  } else if (module === 'observability') {
    setObservabilitySubmodule('summary')
  } else {
    setRuntimeSubmodule('connections')
  }
}

function handleSettingsSubmoduleChange(
  module: SettingsModule,
  submodule: SettingsSubmodule,
) {
  setSettingsModule(module)
  if (module === 'authoring') {
    setAuthoringSubmodule(submodule as AuthoringSubmodule)
  } else if (module === 'observability') {
    setObservabilitySubmodule(submodule as ObservabilitySubmodule)
  } else {
    setRuntimeSubmodule(submodule as RuntimeSubmodule)
  }
}
```

Replace references to `activeView === 'chat'` with `primaryView === 'chat'`.
Replace `activeView === 'account'` with `primaryView === 'account'`.

- [ ] **Step 3: Update `AppSidebar` props**

Replace the `AppSidebar` call props:

```tsx
activeView={activeView}
onViewChange={setActiveView}
```

with:

```tsx
accountModule={accountModule}
authoringSubmodule={authoringSubmodule}
observabilitySubmodule={observabilitySubmodule}
onAccountModuleChange={setAccountModule}
onPrimaryViewChange={handlePrimaryViewChange}
onSettingsModuleChange={handleSettingsModuleChange}
onSettingsSubmoduleChange={handleSettingsSubmoduleChange}
primaryView={primaryView}
runtimeSubmodule={runtimeSubmodule}
settingsModule={settingsModule}
```

Update the `AppSidebar` parameter list and type:

```ts
function AppSidebar({
  accountModule,
  authoringSubmodule,
  primaryView,
  runtimeSubmodule,
  settingsModule,
  observabilitySubmodule,
  ...
  onAccountModuleChange,
  onPrimaryViewChange,
  onSettingsModuleChange,
  onSettingsSubmoduleChange,
}: {
  accountModule: AccountModule
  authoringSubmodule: AuthoringSubmodule
  primaryView: PrimaryView
  runtimeSubmodule: RuntimeSubmodule
  settingsModule: SettingsModule
  observabilitySubmodule: ObservabilitySubmodule
  ...
  onAccountModuleChange(module: AccountModule): void
  onPrimaryViewChange(view: PrimaryView): void
  onSettingsModuleChange(module: SettingsModule): void
  onSettingsSubmoduleChange(
    module: SettingsModule,
    submodule: SettingsSubmodule,
  ): void
})
```

- [ ] **Step 4: Render contextual sidebar body**

In `AppSidebar`, replace the always-rendered `SessionNavigationPanel` with:

```tsx
{primaryView === 'chat' ? (
  <SessionNavigationPanel
    canLoadMore={canLoadMoreSessions}
    error={error}
    onArchiveSession={onArchiveSession}
    onLoadMore={onLoadMoreSessions}
    onRenameSession={onRenameSession}
    onSelectSession={onSelectSession}
    onStartNewSession={onStartNewSession}
    onStatusFilterChange={onStatusFilterChange}
    onUnarchiveSession={onUnarchiveSession}
    selectedSessionId={selectedSessionId}
    sessions={sessions}
    statusFilter={statusFilter}
    state={sessionState}
  />
) : primaryView === 'account' ? (
  <AccountNavigationPanel
    activeModule={accountModule}
    onModuleChange={onAccountModuleChange}
  />
) : (
  <SettingsNavigationPanel
    activeAuthoringSubmodule={authoringSubmodule}
    activeModule={settingsModule}
    activeObservabilitySubmodule={observabilitySubmodule}
    activeRuntimeSubmodule={runtimeSubmodule}
    onModuleChange={onSettingsModuleChange}
    onSubmoduleChange={onSettingsSubmoduleChange}
  />
)}
```

- [ ] **Step 5: Add account/settings navigation components**

Add these components below `SidebarNavButton`:

```tsx
function AccountNavigationPanel({
  activeModule,
  onModuleChange,
}: {
  activeModule: AccountModule
  onModuleChange(module: AccountModule): void
}) {
  return (
    <nav className="contextual-navigation" aria-label="My account navigation">
      <h2 className="sidebar-section-title">My account</h2>
      {ACCOUNT_MODULES.map((module) => (
        <button
          aria-pressed={module.id === activeModule}
          className={
            module.id === activeModule
              ? 'contextual-nav-button contextual-nav-button-active'
              : 'contextual-nav-button'
          }
          disabled={module.disabled}
          key={module.id}
          onClick={() => onModuleChange(module.id)}
          type="button"
        >
          {module.label}
        </button>
      ))}
    </nav>
  )
}

function SettingsNavigationPanel({
  activeAuthoringSubmodule,
  activeModule,
  activeObservabilitySubmodule,
  activeRuntimeSubmodule,
  onModuleChange,
  onSubmoduleChange,
}: {
  activeAuthoringSubmodule: AuthoringSubmodule
  activeModule: SettingsModule
  activeObservabilitySubmodule: ObservabilitySubmodule
  activeRuntimeSubmodule: RuntimeSubmodule
  onModuleChange(module: SettingsModule): void
  onSubmoduleChange(module: SettingsModule, submodule: SettingsSubmodule): void
}) {
  return (
    <nav className="contextual-navigation" aria-label="Settings navigation">
      <h2 className="sidebar-section-title">Settings</h2>
      {SETTINGS_NAVIGATION.map((module) => {
        const moduleActive = module.id === activeModule
        return (
          <div className="contextual-nav-group" key={module.id}>
            <button
              aria-expanded={moduleActive}
              aria-pressed={moduleActive}
              className={
                moduleActive
                  ? 'contextual-nav-button contextual-nav-button-active'
                  : 'contextual-nav-button'
              }
              onClick={() => onModuleChange(module.id)}
              type="button"
            >
              {module.label}
            </button>
            <div className="contextual-nav-sublist">
              {module.submodules.map((submodule) => {
                const activeSubmodule = getActiveSettingsSubmodule({
                  activeAuthoringSubmodule,
                  activeObservabilitySubmodule,
                  activeRuntimeSubmodule,
                  module: module.id,
                })
                const active = moduleActive && activeSubmodule === submodule.id
                return (
                  <button
                    aria-pressed={active}
                    className={
                      active
                        ? 'contextual-nav-subbutton contextual-nav-subbutton-active'
                        : 'contextual-nav-subbutton'
                    }
                    key={submodule.id}
                    onClick={() => onSubmoduleChange(module.id, submodule.id)}
                    type="button"
                  >
                    {submodule.label}
                  </button>
                )
              })}
            </div>
          </div>
        )
      })}
    </nav>
  )
}

function getActiveSettingsSubmodule({
  activeAuthoringSubmodule,
  activeObservabilitySubmodule,
  activeRuntimeSubmodule,
  module,
}: {
  activeAuthoringSubmodule: AuthoringSubmodule
  activeObservabilitySubmodule: ObservabilitySubmodule
  activeRuntimeSubmodule: RuntimeSubmodule
  module: SettingsModule
}): SettingsSubmodule {
  if (module === 'authoring') return activeAuthoringSubmodule
  if (module === 'observability') return activeObservabilitySubmodule
  return activeRuntimeSubmodule
}
```

- [ ] **Step 6: Update primary nav buttons**

In `AppSidebar`, replace:

```tsx
active={activeView === 'chat'}
onClick={() => onViewChange('chat')}
```

with:

```tsx
active={primaryView === 'chat'}
onClick={() => onPrimaryViewChange('chat')}
```

Replace:

```tsx
active={activeView === 'account'}
onClick={() => onViewChange('account')}
```

with:

```tsx
active={primaryView === 'account'}
onClick={() => onPrimaryViewChange('account')}
```

Replace:

```tsx
active={activeView !== 'chat' && activeView !== 'account'}
onClick={() => onViewChange('settings')}
```

with:

```tsx
active={primaryView === 'settings'}
onClick={() => onPrimaryViewChange('settings')}
```

- [ ] **Step 7: Add sidebar CSS**

Add to `frontend/src/App.css` after `.sidebar-nav-button-active`:

```css
.contextual-navigation {
  border-top: 1px solid var(--app-border);
  display: grid;
  gap: 10px;
  padding-top: 18px;
}

.sidebar-section-title {
  color: var(--app-text-strong);
  font-size: 14px;
  line-height: 1.2;
  text-transform: uppercase;
}

.contextual-nav-group {
  display: grid;
  gap: 6px;
}

.contextual-nav-button,
.contextual-nav-subbutton {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  color: var(--app-text-muted);
  justify-content: flex-start;
  min-height: 38px;
  padding: 0 10px;
  text-align: left;
  width: 100%;
}

.contextual-nav-subbutton {
  font-size: 13px;
  min-height: 34px;
  padding-left: 22px;
}

.contextual-nav-button:hover,
.contextual-nav-button-active,
.contextual-nav-subbutton:hover,
.contextual-nav-subbutton-active {
  background: var(--app-accent-soft);
  border-color: var(--app-border-strong);
  color: var(--app-text-strong);
}

.contextual-nav-button:disabled {
  background: transparent;
  border-color: transparent;
  color: var(--app-text-muted);
  cursor: not-allowed;
  opacity: 0.55;
}
```

- [ ] **Step 8: Run focused sidebar tests**

Run:

```powershell
pnpm --dir frontend test -- App.test.tsx -t "sidebar|submodules"
```

Expected: the primary contextual sidebar tests pass. Tests that expect focused content may still fail until Task 4.

- [ ] **Step 9: Commit navigation shell**

Run:

```powershell
git add -- frontend/src/App.tsx frontend/src/App.css frontend/src/App.test.tsx
git commit -m "feat: add contextual sidebar navigation"
```

Expected: one commit containing explicit navigation state, contextual sidebar bodies and sidebar styles.

---

### Task 4: Route Account, Authoring and Observability Content by Submodule

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Replace `activeSettingsSection` derivation**

Remove:

```ts
const activeSettingsSection: SettingsSection =
  activeView === 'authoring' ||
  activeView === 'observability' ||
  activeView === 'runtime'
    ? activeView
    : 'authoring'
```

Use the explicit state directly in render:

```ts
const activeSettingsModule = settingsModule
```

- [ ] **Step 2: Make `SettingsPanel` a shell only**

Replace the current `SettingsPanel` signature and body:

```tsx
function SettingsPanel({
  activeSection,
  children,
  onSectionChange,
}: {
  activeSection: SettingsSection
  children: ReactNode
  onSectionChange(section: SettingsSection): void
}) {
  return (
    <section className="settings-shell" aria-labelledby="settings-title">
      ...
      <div className="settings-section-body">{children}</div>
    </section>
  )
}
```

with:

```tsx
function SettingsPanel({ children }: { children: ReactNode }) {
  return (
    <section className="settings-shell" aria-labelledby="settings-title">
      <header className="settings-shell-header">
        <div>
          <p className="panel-label">Settings</p>
          <h2 id="settings-title">Settings</h2>
        </div>
      </header>
      <div className="settings-section-body">{children}</div>
    </section>
  )
}
```

- [ ] **Step 3: Update main render routing**

Replace:

```tsx
{activeView === 'chat' ? (
  ...
) : activeView === 'account' ? (
  <AppearanceSettingsPanel onThemeChange={setTheme} theme={theme} />
) : (
  <SettingsPanel
    activeSection={activeSettingsSection}
    onSectionChange={setActiveView}
  >
    {activeSettingsSection === 'observability' ? (
      <ObservabilityPanel ... />
    ) : activeSettingsSection === 'runtime' ? (
      <RuntimeSettingsPanel ... />
    ) : (
      <AuthoringPanel ... />
    )}
  </SettingsPanel>
)}
```

with:

```tsx
{primaryView === 'chat' ? (
  ...
) : primaryView === 'account' ? (
  accountModule === 'appearance' ? (
    <AppearanceSettingsPanel onThemeChange={setTheme} theme={theme} />
  ) : (
    <DeferredAccountModulePanel moduleName="Memory" />
  )
) : (
  <SettingsPanel>
    {activeSettingsModule === 'observability' ? (
      <ObservabilityPanel
        activeSubmodule={observabilitySubmodule}
        createdAtFrom={createdAtFrom}
        createdAtTo={createdAtTo}
        error={observabilityError}
        onCreatedAtFromChange={setCreatedAtFrom}
        onCreatedAtToChange={setCreatedAtTo}
        onProjectIdChange={handleChangeProjectId}
        onRefresh={() => void handleRefreshObservability()}
        onStatusChange={setObservabilityStatus}
        projectId={projectId}
        state={observabilityState}
        status={observabilityStatus}
        summary={observabilitySummary}
      />
    ) : activeSettingsModule === 'runtime' ? (
      <RuntimeSettingsPanel
        activeSubmodule={runtimeSubmodule}
        ...
      />
    ) : (
      <AuthoringPanel
        activeSubmodule={authoringSubmodule}
        ...
      />
    )}
  </SettingsPanel>
)}
```

Keep the existing full prop lists for `RuntimeSettingsPanel` and `AuthoringPanel`; only add the `activeSubmodule` prop.

- [ ] **Step 4: Add deferred account panel**

Add below `AppearanceSettingsPanel`:

```tsx
function DeferredAccountModulePanel({ moduleName }: { moduleName: string }) {
  return (
    <section className="panel settings-panel" aria-labelledby="deferred-account-title">
      <header className="settings-header">
        <div>
          <p className="panel-label">My account</p>
          <h2 id="deferred-account-title">{moduleName}</h2>
        </div>
        <span className="status">Deferred</span>
      </header>
      <p className="settings-description">
        This module is not available until a durable backend contract exists.
      </p>
    </section>
  )
}
```

- [ ] **Step 5: Filter `AuthoringPanel` by submodule**

Update `AuthoringPanel` props:

```ts
activeSubmodule: AuthoringSubmodule
```

At the start of the returned JSX, replace `<div className="authoring-grid">` content with conditional render blocks:

```tsx
return (
  <div className="authoring-grid authoring-grid-focused">
    {activeSubmodule === 'projects' ? (
      <section className="panel authoring-panel" aria-labelledby="projects-title">
        ...
      </section>
    ) : null}

    {activeSubmodule === 'users' ? (
      <ProjectAccessPanel ... />
    ) : null}

    {activeSubmodule === 'sources' ? (
      <section className="panel authoring-panel" aria-labelledby="sources-title">
        ...
      </section>
    ) : null}

    {activeSubmodule === 'knowledge' ? (
      <KnowledgeReviewPanel ... />
    ) : null}
  </div>
)
```

Move the existing four panel blocks into the matching conditional branches without changing their inner forms or props.

- [ ] **Step 6: Rename the users heading**

Inside `ProjectAccessPanel`, change the heading to make the submodule test clear:

```tsx
<p className="panel-label">Users</p>
<h2 id="project-access-title">Users</h2>
```

If a test currently queries the old heading, update it to query either `Users` or a role/label inside the same region.

- [ ] **Step 7: Filter `ObservabilityPanel` by submodule**

Update `ObservabilityPanel` props:

```ts
activeSubmodule: ObservabilitySubmodule
```

Change the heading:

```tsx
<p className="panel-label">Observability</p>
<h2 id="observability-title">{observabilitySubmoduleLabel(activeSubmodule)}</h2>
```

Add helper near status helpers:

```ts
function observabilitySubmoduleLabel(submodule: ObservabilitySubmodule): string {
  if (submodule === 'costs') return 'Costs'
  if (submodule === 'errors') return 'Errors'
  if (submodule === 'latency') return 'Latency'
  return 'Summary'
}
```

Keep the filter form visible for all observability submodules in the first implementation. Render `ObservabilityMetrics` for every submodule until smaller metric components are extracted:

```tsx
<ObservabilityMetrics summary={summary} />
```

- [ ] **Step 8: Run focused tests**

Run:

```powershell
pnpm --dir frontend test -- App.test.tsx -t "account modules|settings modules|routes settings"
```

Expected: PASS for account and non-runtime settings routing.

- [ ] **Step 9: Commit focused account/settings content**

Run:

```powershell
git add -- frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: route settings content by sidebar submodule"
```

Expected: one commit containing account, authoring and observability routing.

---

### Task 5: Split Runtime UI into Submodule Panels

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Update `RuntimeSettingsPanel` props**

Add:

```ts
activeSubmodule: RuntimeSubmodule
```

to the destructured props and type block for `RuntimeSettingsPanel`.

- [ ] **Step 2: Replace the generic Runtime header and button**

Inside `RuntimeSettingsPanel`, remove:

```tsx
<button
  className="secondary-button"
  disabled={state === 'loading'}
  onClick={onRefresh}
  type="button"
>
  {state === 'loading' ? 'Refreshing...' : 'Refresh runtime'}
</button>
```

Keep the error block:

```tsx
{error ? (
  <p className="form-feedback form-feedback-error" role="alert">
    {error}
  </p>
) : null}
```

- [ ] **Step 3: Create `RuntimeConnectionsPanel`**

Move the existing first runtime panel content for provider connections, connection form and secret form into:

```tsx
function RuntimeConnectionsPanel({
  connectionBaseUrl,
  connectionCapabilities,
  connectionProvider,
  connectionType,
  connections,
  onConnectionBaseUrlChange,
  onConnectionCapabilitiesChange,
  onConnectionProviderChange,
  onConnectionTypeChange,
  onRefresh,
  onSaveConnection,
  onSaveSecret,
  onSecretConnectionIdChange,
  onSecretValueChange,
  secretConnectionId,
  secretValue,
  state,
}: {
  connectionBaseUrl: string
  connectionCapabilities: string
  connectionProvider: string
  connectionType: string
  connections: ProviderConnection[]
  onConnectionBaseUrlChange(value: string): void
  onConnectionCapabilitiesChange(value: string): void
  onConnectionProviderChange(value: string): void
  onConnectionTypeChange(value: string): void
  onRefresh(): void
  onSaveConnection(event: FormEvent<HTMLFormElement>): void
  onSaveSecret(event: FormEvent<HTMLFormElement>): void
  onSecretConnectionIdChange(value: string): void
  onSecretValueChange(value: string): void
  secretConnectionId: string
  secretValue: string
  state: RequestState
}) {
  return (
    <section className="panel runtime-panel" aria-labelledby="runtime-connections-title">
      <div className="panel-heading">
        <div>
          <p className="panel-label">Runtime</p>
          <h2 id="runtime-connections-title">Connections</h2>
        </div>
        <span className={statusClassName(state)}>{runtimeStatusLabel(state)}</span>
      </div>
      <button
        className="secondary-button"
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
      >
        {state === 'loading' ? 'Refreshing...' : 'Refresh connections'}
      </button>
      {/* Move existing Provider connections list, Save connection form and Save secret form here unchanged. */}
    </section>
  )
}
```

When implementing, replace the comment with the exact existing JSX sections:

- `<section className="runtime-section" aria-label="Provider connections">`
- `<form className="authoring-form" onSubmit={onSaveConnection}>`
- `<form className="authoring-form" onSubmit={onSaveSecret}>`

- [ ] **Step 4: Create `RuntimeModelCatalogPanel`**

Move model sync and provider catalog into:

```tsx
function RuntimeModelCatalogPanel({
  connections,
  modelSyncConnectionId,
  onModelSyncConnectionIdChange,
  onRefresh,
  onSyncProviderModels,
  providerModels,
  state,
}: {
  connections: ProviderConnection[]
  modelSyncConnectionId: string
  onModelSyncConnectionIdChange(value: string): void
  onRefresh(): void
  onSyncProviderModels(event: FormEvent<HTMLFormElement>): void
  providerModels: ProviderModel[]
  state: RequestState
}) {
  return (
    <section className="panel runtime-panel" aria-labelledby="runtime-model-catalog-title">
      <div className="panel-heading">
        <div>
          <p className="panel-label">Runtime</p>
          <h2 id="runtime-model-catalog-title">Model catalog</h2>
        </div>
        <span className={statusClassName(state)}>{runtimeStatusLabel(state)}</span>
      </div>
      <button
        className="secondary-button"
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
      >
        {state === 'loading' ? 'Refreshing...' : 'Refresh catalog'}
      </button>
      <form className="authoring-form" onSubmit={onSyncProviderModels}>
        <div className="runtime-form-grid">
          <label className="field runtime-field-wide">
            <span>Model sync connection</span>
            <ConnectionSelect
              connections={connections}
              onChange={onModelSyncConnectionIdChange}
              testId="model-sync-connection-select"
              value={modelSyncConnectionId}
            />
          </label>
        </div>
        <button type="submit">Sync models</button>
      </form>
      <ProviderModelCatalogView providerModels={providerModels} />
    </section>
  )
}
```

- [ ] **Step 5: Create `RuntimeGlobalDefaultsPanel`**

Move global slots, chat models and global chat retrieval into:

```tsx
function RuntimeGlobalDefaultsPanel({
  chatConnectionId,
  chatModelId,
  chatModelOptions,
  chatModels,
  chatRetrievalSettings,
  chatSyncMessage,
  globalChatRerankCandidateLimit,
  globalChatRerankEnabled,
  globalChatRetrievalLimit,
  globalSlot,
  globalSlotConnectionId,
  globalSlotConnections,
  globalSlotModelId,
  globalSlotModelOptions,
  globalSlotSyncMessage,
  onChatConnectionIdChange,
  onChatModelIdChange,
  onGlobalChatRerankCandidateLimitChange,
  onGlobalChatRerankEnabledChange,
  onGlobalChatRetrievalLimitChange,
  onGlobalSlotChange,
  onGlobalSlotConnectionIdChange,
  onGlobalSlotModelIdChange,
  onRefresh,
  onSaveGlobalChatModel,
  onSaveGlobalChatRetrieval,
  onSaveGlobalSlot,
  slots,
  state,
}: {
  chatConnectionId: string
  chatModelId: string
  chatModelOptions: ProviderModelOption[]
  chatModels: ChatModel[]
  chatRetrievalSettings: ChatRetrievalSettings | null
  chatSyncMessage: string | null
  globalChatRerankCandidateLimit: number
  globalChatRerankEnabled: boolean
  globalChatRetrievalLimit: number
  globalSlot: string
  globalSlotConnectionId: string
  globalSlotConnections: ProviderConnection[]
  globalSlotModelId: string
  globalSlotModelOptions: ProviderModelOption[]
  globalSlotSyncMessage: string | null
  onChatConnectionIdChange(value: string): void
  onChatModelIdChange(value: string): void
  onGlobalChatRerankCandidateLimitChange(value: number): void
  onGlobalChatRerankEnabledChange(value: boolean): void
  onGlobalChatRetrievalLimitChange(value: number): void
  onGlobalSlotChange(value: string): void
  onGlobalSlotConnectionIdChange(value: string): void
  onGlobalSlotModelIdChange(value: string): void
  onRefresh(): void
  onSaveGlobalChatModel(event: FormEvent<HTMLFormElement>): void
  onSaveGlobalChatRetrieval(event: FormEvent<HTMLFormElement>): void
  onSaveGlobalSlot(event: FormEvent<HTMLFormElement>): void
  slots: RuntimeSlotDefault[]
  state: RequestState
}) {
  return (
    <section className="panel runtime-panel runtime-panel-wide" aria-labelledby="runtime-global-defaults-title">
      <div className="panel-heading">
        <div>
          <p className="panel-label">Runtime</p>
          <h2 id="runtime-global-defaults-title">Global defaults</h2>
        </div>
        <span className={statusClassName(state)}>{runtimeStatusLabel(state)}</span>
      </div>
      <button
        className="secondary-button"
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
      >
        {state === 'loading' ? 'Refreshing...' : 'Reload global defaults'}
      </button>
      {/* Move existing Global slots, Chat models and Global chat retrieval JSX here unchanged. */}
    </section>
  )
}
```

When implementing, replace the comment with these existing blocks:

- `<RuntimeSlotList slots={slots} />`
- global slot save form
- `<section className="runtime-section" aria-label="Global chat models">`
- global chat default form
- `<section className="runtime-section" aria-label="Global chat retrieval">`

- [ ] **Step 6: Create `RuntimeProjectOverridesPanel`**

Move project runtime settings into:

```tsx
function RuntimeProjectOverridesPanel({
  projectId,
  projectRuntimeSettings,
  projectSlot,
  projectSlotConnectionId,
  projectSlotConnections,
  projectSlotModelId,
  projectSlotModelOptions,
  projectSlotSyncMessage,
  projectChatRerankCandidateLimit,
  projectChatRerankEnabled,
  projectChatRetrievalLimit,
  onProjectChatRerankCandidateLimitChange,
  onProjectChatRerankEnabledChange,
  onProjectChatRetrievalLimitChange,
  onProjectSlotChange,
  onProjectSlotConnectionIdChange,
  onProjectSlotModelIdChange,
  onRefresh,
  onResetProjectChatRetrieval,
  onResetProjectSlot,
  onSaveProjectChatRetrieval,
  onSaveProjectOverride,
  state,
}: {
  projectId: string
  projectRuntimeSettings: ProjectRuntimeSettings | null
  projectSlot: string
  projectSlotConnectionId: string
  projectSlotConnections: ProviderConnection[]
  projectSlotModelId: string
  projectSlotModelOptions: ProviderModelOption[]
  projectSlotSyncMessage: string | null
  projectChatRerankCandidateLimit: number
  projectChatRerankEnabled: boolean
  projectChatRetrievalLimit: number
  onProjectChatRerankCandidateLimitChange(value: number): void
  onProjectChatRerankEnabledChange(value: boolean): void
  onProjectChatRetrievalLimitChange(value: number): void
  onProjectSlotChange(value: string): void
  onProjectSlotConnectionIdChange(value: string): void
  onProjectSlotModelIdChange(value: string): void
  onRefresh(): void
  onResetProjectChatRetrieval(): void
  onResetProjectSlot(slot: string): void
  onSaveProjectChatRetrieval(event: FormEvent<HTMLFormElement>): void
  onSaveProjectOverride(event: FormEvent<HTMLFormElement>): void
  state: RequestState
}) {
  return (
    <section
      className="panel runtime-panel runtime-panel-wide"
      aria-label="Project runtime settings"
    >
      <div className="panel-heading">
        <div>
          <p className="panel-label">Runtime</p>
          <h2>Project overrides</h2>
        </div>
        <span className="status">{projectId.trim() || 'No project'}</span>
      </div>
      <button
        className="secondary-button"
        disabled={state === 'loading'}
        onClick={onRefresh}
        type="button"
      >
        {state === 'loading' ? 'Refreshing...' : 'Reload project settings'}
      </button>
      {/* Move existing ProjectRuntimeSettingsView and project override forms here unchanged. */}
    </section>
  )
}
```

When implementing, replace the comment with these existing blocks:

- `<ProjectRuntimeSettingsView ... />`
- project chat retrieval override form
- project slot override form

- [ ] **Step 7: Route `RuntimeSettingsPanel` by submodule**

Replace the `return` body of `RuntimeSettingsPanel` with:

```tsx
return (
  <div className="runtime-grid runtime-grid-focused">
    {error ? (
      <p className="form-feedback form-feedback-error" role="alert">
        {error}
      </p>
    ) : null}
    {activeSubmodule === 'connections' ? (
      <RuntimeConnectionsPanel
        connectionBaseUrl={connectionBaseUrl}
        connectionCapabilities={connectionCapabilities}
        connectionProvider={connectionProvider}
        connectionType={connectionType}
        connections={connections}
        onConnectionBaseUrlChange={onConnectionBaseUrlChange}
        onConnectionCapabilitiesChange={onConnectionCapabilitiesChange}
        onConnectionProviderChange={onConnectionProviderChange}
        onConnectionTypeChange={onConnectionTypeChange}
        onRefresh={onRefresh}
        onSaveConnection={onSaveConnection}
        onSaveSecret={onSaveSecret}
        onSecretConnectionIdChange={onSecretConnectionIdChange}
        onSecretValueChange={onSecretValueChange}
        secretConnectionId={secretConnectionId}
        secretValue={secretValue}
        state={state}
      />
    ) : null}
    {activeSubmodule === 'model_catalog' ? (
      <RuntimeModelCatalogPanel
        connections={connections}
        modelSyncConnectionId={modelSyncConnectionId}
        onModelSyncConnectionIdChange={onModelSyncConnectionIdChange}
        onRefresh={onRefresh}
        onSyncProviderModels={onSyncProviderModels}
        providerModels={providerModels}
        state={state}
      />
    ) : null}
    {activeSubmodule === 'global_defaults' ? (
      <RuntimeGlobalDefaultsPanel
        chatConnectionId={chatConnectionId}
        chatModelId={chatModelId}
        chatModelOptions={chatModelOptions}
        chatModels={chatModels}
        chatRetrievalSettings={chatRetrievalSettings}
        chatSyncMessage={chatSyncMessage}
        globalChatRerankCandidateLimit={globalChatRerankCandidateLimit}
        globalChatRerankEnabled={globalChatRerankEnabled}
        globalChatRetrievalLimit={globalChatRetrievalLimit}
        globalSlot={globalSlot}
        globalSlotConnectionId={globalSlotConnectionId}
        globalSlotConnections={globalSlotConnections}
        globalSlotModelId={globalSlotModelId}
        globalSlotModelOptions={globalSlotModelOptions}
        globalSlotSyncMessage={globalSlotSyncMessage}
        onChatConnectionIdChange={onChatConnectionIdChange}
        onChatModelIdChange={onChatModelIdChange}
        onGlobalChatRerankCandidateLimitChange={onGlobalChatRerankCandidateLimitChange}
        onGlobalChatRerankEnabledChange={onGlobalChatRerankEnabledChange}
        onGlobalChatRetrievalLimitChange={onGlobalChatRetrievalLimitChange}
        onGlobalSlotChange={onGlobalSlotChange}
        onGlobalSlotConnectionIdChange={onGlobalSlotConnectionIdChange}
        onGlobalSlotModelIdChange={onGlobalSlotModelIdChange}
        onRefresh={onRefresh}
        onSaveGlobalChatModel={onSaveGlobalChatModel}
        onSaveGlobalChatRetrieval={onSaveGlobalChatRetrieval}
        onSaveGlobalSlot={onSaveGlobalSlot}
        slots={slots}
        state={state}
      />
    ) : null}
    {activeSubmodule === 'project_overrides' ? (
      <RuntimeProjectOverridesPanel
        onProjectChatRerankCandidateLimitChange={onProjectChatRerankCandidateLimitChange}
        onProjectChatRerankEnabledChange={onProjectChatRerankEnabledChange}
        onProjectChatRetrievalLimitChange={onProjectChatRetrievalLimitChange}
        onProjectSlotChange={onProjectSlotChange}
        onProjectSlotConnectionIdChange={onProjectSlotConnectionIdChange}
        onProjectSlotModelIdChange={onProjectSlotModelIdChange}
        onRefresh={onRefresh}
        onResetProjectChatRetrieval={onResetProjectChatRetrieval}
        onResetProjectSlot={onResetProjectSlot}
        onSaveProjectChatRetrieval={onSaveProjectChatRetrieval}
        onSaveProjectOverride={onSaveProjectOverride}
        projectChatRerankCandidateLimit={projectChatRerankCandidateLimit}
        projectChatRerankEnabled={projectChatRerankEnabled}
        projectChatRetrievalLimit={projectChatRetrievalLimit}
        projectId={projectId}
        projectRuntimeSettings={projectRuntimeSettings}
        projectSlot={projectSlot}
        projectSlotConnectionId={projectSlotConnectionId}
        projectSlotConnections={projectSlotConnections}
        projectSlotModelId={projectSlotModelId}
        projectSlotModelOptions={projectSlotModelOptions}
        projectSlotSyncMessage={projectSlotSyncMessage}
        state={state}
      />
    ) : null}
  </div>
)
```

- [ ] **Step 8: Update Runtime tests to navigate submodules**

In `frontend/src/App.test.tsx`, update Runtime test setup:

Replace:

```ts
await openSettingsSection(user, 'Runtime')
await user.click(screen.getByRole('button', { name: 'Refresh runtime' }))
```

with:

```ts
await openSettingsSubmodule(user, 'Runtime', 'Connections')
await user.click(screen.getByRole('button', { name: 'Refresh connections' }))
```

Before model sync assertions, add:

```ts
await openSettingsSubmodule(user, 'Runtime', 'Model catalog')
await user.click(screen.getByRole('button', { name: 'Refresh catalog' }))
```

Before global slot/global retrieval assertions, add:

```ts
await openSettingsSubmodule(user, 'Runtime', 'Global defaults')
await user.click(screen.getByRole('button', { name: 'Reload global defaults' }))
```

In project override tests, use:

```ts
await openSettingsSubmodule(user, 'Runtime', 'Project overrides')
await user.click(screen.getByRole('button', { name: 'Reload project settings' }))
```

Add this assertion to the first Runtime test:

```ts
expect(screen.queryByRole('button', { name: 'Refresh runtime' })).toBeNull()
```

- [ ] **Step 9: Run Runtime tests**

Run:

```powershell
pnpm --dir frontend test -- App.test.tsx -t "runtime"
```

Expected: PASS for Runtime tests. If multiple identical labels exist after panel splitting, scope queries with `within(screen.getByRole('region', { name: ... }))` instead of changing visible labels.

- [ ] **Step 10: Commit Runtime split**

Run:

```powershell
git add -- frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: split runtime settings into submodules"
```

Expected: one commit containing Runtime panel split and updated Runtime tests.

---

### Task 6: Polish Layout and Run Frontend Validation

**Files:**
- Modify: `frontend/src/App.css`
- Test: frontend commands

- [ ] **Step 1: Add focused grid styles**

Add to `frontend/src/App.css` near `.authoring-grid` and `.runtime-grid`:

```css
.authoring-grid-focused,
.runtime-grid-focused {
  grid-template-columns: minmax(0, 1fr);
}

.authoring-grid-focused .authoring-panel,
.runtime-grid-focused .runtime-panel {
  min-height: auto;
}
```

- [ ] **Step 2: Remove unused tab styles only after confirming no references**

Run:

```powershell
rg -n "settings-section-tabs|settings-section-tab" frontend/src
```

Expected before cleanup: only `frontend/src/App.css` contains those selectors.

Delete these CSS blocks if no JSX references remain:

```css
.settings-section-tabs { ... }
.settings-section-tab { ... }
.settings-section-tab-active { ... }
```

- [ ] **Step 3: Run full frontend test file**

Run:

```powershell
pnpm --dir frontend test -- App.test.tsx
```

Expected: all `App.test.tsx` tests pass.

- [ ] **Step 4: Run frontend typecheck**

Run:

```powershell
pnpm --dir frontend typecheck
```

Expected: exits `0` with no TypeScript errors.

- [ ] **Step 5: Run frontend lint**

Run:

```powershell
pnpm --dir frontend lint
```

Expected: exits `0` with no ESLint errors.

- [ ] **Step 6: Run frontend build**

Run:

```powershell
pnpm --dir frontend build
```

Expected: exits `0` and Vite emits a production build.

- [ ] **Step 7: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected: exits `0` with no whitespace errors.

- [ ] **Step 8: Commit validation polish**

Run:

```powershell
git add -- frontend/src/App.css frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "style: polish contextual navigation layout"
```

Expected: one commit only if files changed after Task 5. If no files changed, skip this commit.

---

### Task 7: Archive OpenSpec Change and Update Project Docs

**Files:**
- Modify: `openspec/specs/chat-frontend/spec.md`
- Move: `openspec/changes/runtime-navigation-clarity/` to archive path through OpenSpec archive command
- Modify: `docs/progress.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Validate all OpenSpec specs**

Run:

```powershell
npx --yes @fission-ai/openspec validate --specs --strict --no-interactive
```

Expected: exits `0`.

- [ ] **Step 2: Archive the OpenSpec change**

Run:

```powershell
npx --yes @fission-ai/openspec archive runtime-navigation-clarity --yes
```

Expected: the change moves under `openspec/changes/archive/2026-06-29-runtime-navigation-clarity/` and the canonical `openspec/specs/chat-frontend/spec.md` receives the accepted deltas.

- [ ] **Step 3: Update progress docs**

In `docs/progress.md`, update:

```markdown
## Ultimo slice completado

Runtime navigation clarity: el sidebar izquierdo ahora muestra navegacion
contextual. `Chat` conserva sesiones; `My account` muestra modulos de cuenta;
`Settings` muestra `Authoring`, `Observability` y `Runtime` con submodulos.
Runtime queda separado en `Connections`, `Model catalog`, `Global defaults` y
`Project overrides`; el boton generico `Refresh runtime` fue reemplazado por
acciones especificas por submodulo.
```

Also update:

```markdown
## Change OpenSpec activo

No active changes found.
```

and:

```markdown
## Ultimo change archivado

- `openspec/changes/archive/2026-06-29-runtime-navigation-clarity/`
```

- [ ] **Step 4: Update roadmap docs**

In `docs/roadmap.md`, add to current state:

```markdown
- Post-M38 Runtime navigation clarity: completo.
```

Add a short section after M38:

```markdown
## Post-M38 Runtime navigation clarity

Estado: completo.

Entregado:

- Sidebar contextual para `Chat`, `My account` y `Settings`.
- Settings con arbol de `Authoring`, `Observability` y `Runtime`.
- Runtime separado en `Connections`, `Model catalog`, `Global defaults` y
  `Project overrides`.
- Eliminado el boton generico `Refresh runtime` a favor de acciones especificas.
```

- [ ] **Step 5: Run final validation**

Run:

```powershell
pnpm --dir frontend test -- App.test.tsx
pnpm --dir frontend typecheck
pnpm --dir frontend lint
pnpm --dir frontend build
npx --yes @fission-ai/openspec validate --specs --strict --no-interactive
git diff --check
```

Expected: all commands exit `0`.

- [ ] **Step 6: Commit closeout**

Run:

```powershell
git add -- docs/progress.md docs/roadmap.md openspec
git commit -m "docs: close runtime navigation clarity"
```

Expected: final docs/OpenSpec closeout commit.

---

## Self-Review

Spec coverage:

- Contextual sidebar: Task 2 defines failing tests, Task 3 implements sidebar bodies.
- Chat session sidebar preserved: Task 3 renders `SessionNavigationPanel` only for `Chat`.
- My account modules: Task 3 adds account nav, Task 4 routes `Appearance` and deferred `Memory`.
- Settings tree and submodules: Task 3 adds grouped settings nav, Task 4 routes Authoring/Observability, Task 5 routes Runtime.
- Runtime split: Task 5 creates four Runtime panels and removes generic `Refresh runtime`.
- Runtime safety rules: Task 5 updates existing Runtime tests while preserving no-secret and inheritance assertions.
- OpenSpec/docs: Task 1 adds contract, Task 7 archives and updates progress/roadmap.
- Verification: Tasks 1, 6 and 7 include OpenSpec, frontend tests, typecheck, lint, build and whitespace checks.

Completeness scan:

- No unresolved marker text or unconstrained planning steps remain.
- The two JSX move steps in Runtime identify exact existing blocks to move and exact wrapper components to use.

Type consistency:

- Navigation types use `PrimaryView`, `AccountModule`, `SettingsModule`, `AuthoringSubmodule`, `ObservabilitySubmodule`, `RuntimeSubmodule` and `SettingsSubmodule` consistently.
- Test helper `openSettingsSubmodule` matches the sidebar navigation names defined in implementation.
- Runtime submodule ids match `connections`, `model_catalog`, `global_defaults` and `project_overrides` across state, navigation and render routing.
