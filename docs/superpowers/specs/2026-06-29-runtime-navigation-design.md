# Runtime and Navigation Clarity Design

## Goal

Make the app easier to understand by turning the left sidebar into contextual
navigation and splitting Runtime into smaller, named submodules. The current
problem is that `Settings` can be selected while the sidebar still shows chat
sessions, and the Runtime screen combines provider infrastructure, model sync,
global defaults, chat retrieval defaults and project overrides behind one
generic `Refresh runtime` button.

## Approved Direction

Use the left sidebar as the source of truth for secondary navigation:

- `Chat` keeps the current session navigation.
- `My account` shows account modules such as `Appearance` and `Memory`.
- `Settings` shows settings modules and their submodules.
- Internal `Settings` tabs are removed from the main content area.
- Runtime refresh becomes automatic loading plus specific submodule actions.

## Information Architecture

The project selector remains common at the top of the sidebar because project
context is shared by chat, authoring, observability and project runtime
overrides.

Primary navigation remains:

- `Chat`
- `My account`
- `Settings`

Contextual sidebar content changes by primary navigation state.

### Chat

`Chat` keeps the existing session panel with:

- new chat action;
- active, training and archived session filters;
- session selection, rename, archive and unarchive behavior;
- load more behavior.

No session list is shown when the user is in `My account` or `Settings`.

### My account

`My account` shows account-level modules:

- `Appearance`: current theme settings.
- `Memory`: visible only as unavailable/deferred unless a real durable memory
  contract exists. It must not render fake memory state.

The first implemented account module is `Appearance`, preserving the existing
theme behavior: `data-theme`, dark class handling and local persistence.

### Settings

`Settings` shows a tree:

- `Authoring`
  - `Projects`
  - `Users`
  - `Knowledge`
  - `Sources`
- `Observability`
  - `Summary`
  - `Costs`
  - `Errors`
  - `Latency`
- `Runtime`
  - `Connections`
  - `Model catalog`
  - `Global defaults`
  - `Project overrides`

The tree can be implemented as grouped buttons with indentation. It does not
need a third-party router for this slice.

## Runtime Submodules

Runtime keeps the existing backend contracts and separates them visually.

### Connections

Purpose: manage provider infrastructure.

Content:

- configured provider connections;
- provider, connection type, base URL and capabilities form;
- safe secret status;
- save/rotate secret form.

Rules:

- hosted and local connections can be visible at the same time;
- no plaintext API key, ciphertext or Authorization header is rendered;
- connection IDs remain backend-owned and are not typed by the user.

Refresh behavior:

- load connections when entering the submodule;
- expose `Refresh connections` if manual reload is needed.

### Model catalog

Purpose: inspect and sync provider models for an existing connection.

Content:

- model sync connection selector;
- `Sync models` action;
- provider model catalog grouped by connection and capability.

Refresh behavior:

- load catalog when entering the submodule;
- `Sync models` is explicit and replaces the vague idea of refreshing all
  runtime state.

### Global defaults

Purpose: configure global runtime defaults used by projects unless overridden.

Content:

- fixed runtime slots: `chat`, `dense_embedding`, `sparse_embedding`, `rerank`
  and `contextualization`;
- global slot connection/model selectors filtered by capability;
- global chat model pool with one default;
- global chat retrieval defaults.

Rules:

- do not redesign slots as arbitrary user-defined slots;
- preserve one default model in the chat pool;
- keep model selectors backed by the persisted provider model catalog.

Refresh behavior:

- load global slots, chat models and chat retrieval defaults when entering the
  submodule;
- expose specific reload or save actions only where useful.

### Project overrides

Purpose: show and edit the selected project's effective runtime settings.

Content:

- effective slot list showing inherited versus overridden state;
- reset-to-global actions for overridden slots;
- project slot override form;
- project chat retrieval override form.

Rules:

- project overrides never ask for provider secrets;
- project overrides preserve the split between global provider infrastructure
  and project-scoped defaults;
- changing the selected project clears stale selected chat sessions and reloads
  effective project runtime settings.

Refresh behavior:

- load effective project runtime settings when entering the submodule and when
  project context changes;
- expose `Reload project settings`, not `Refresh runtime`.

## Component Boundaries

The implementation should split current large panels into smaller render units:

- `AppSidebar` chooses one contextual sidebar body from the active primary
  view.
- `SessionNavigationPanel` remains the chat sidebar body.
- New account navigation renders account modules.
- New settings navigation renders grouped settings modules and submodules.
- `SettingsPanel` becomes a content shell, not a tab owner.
- `AuthoringPanel` is split or filtered by submodule so each settings route
  shows one coherent unit.
- `ObservabilityPanel` is split or filtered by submodule while reusing the same
  loaded summary data.
- `RuntimeSettingsPanel` is split into `RuntimeConnectionsPanel`,
  `RuntimeModelCatalogPanel`, `RuntimeGlobalDefaultsPanel` and
  `RuntimeProjectOverridesPanel`.

The first implementation may keep state in `App.tsx` if that is the smallest
safe step, but render boundaries should be named after the submodules so future
extraction is straightforward.

## State and Data Loading

Use explicit navigation state instead of overloading `activeView` with both
primary and settings section values.

Recommended shape:

- `primaryView`: `chat | account | settings`
- `accountModule`: starts as `appearance`
- `settingsModule`: `authoring | observability | runtime`
- `settingsSubmodule`: scoped to the selected settings module

Runtime loading should become demand-driven:

- entering `Connections` loads provider connections;
- entering `Model catalog` loads connections and provider models;
- entering `Global defaults` loads connections, provider models, global slots,
  chat models and chat retrieval defaults;
- entering `Project overrides` loads connections, provider models and effective
  project runtime settings.

The existing helper that fetches all runtime data can remain internally during
the first slice, but the UI should no longer expose a generic `Refresh runtime`
action.

## Error Handling

Errors should be scoped to the submodule that triggered them:

- connection load/save/secret errors stay in `Connections`;
- model sync/catalog errors stay in `Model catalog`;
- global slot/chat default errors stay in `Global defaults`;
- project override errors stay in `Project overrides`.

If a shared fetch fails, show the relevant error only where the missing data is
needed. Do not clear valid user input when refresh, sync or save fails.

## Testing Strategy

Add or update frontend tests for:

- primary sidebar still has exactly `Chat`, `My account` and `Settings`;
- `Chat` shows sessions in the sidebar;
- `My account` does not show sessions and shows account modules;
- `Settings` does not show sessions and shows grouped module navigation;
- selecting `Authoring > Projects`, `Users`, `Knowledge` and `Sources` renders
  the expected focused content;
- selecting Runtime submodules renders only the relevant runtime content;
- no generic `Refresh runtime` button is rendered;
- runtime secrets are still never rendered after save or reload;
- project override inheritance and reset behavior still work;
- existing theme persistence tests continue to pass.

Run at minimum:

```text
pnpm --dir frontend test -- App.test.tsx
pnpm --dir frontend typecheck
pnpm --dir frontend lint
pnpm --dir frontend build
git diff --check
```

The broader implementation plan should decide whether this also needs an
OpenSpec change before code changes. Because the canonical `chat-frontend` spec
currently describes Runtime settings and workflow navigation, a frontend
information-architecture change should update that contract if it changes
observable behavior.

## Out of Scope

- New backend routes.
- New durable memory storage.
- A full URL router.
- New provider types or runtime slot names.
- Changing the provider runtime resolution contract.
- Live-provider validation or Qwen credential requirements.

## Acceptance Criteria

- When `Settings` is selected, the sidebar no longer shows chat sessions.
- Runtime is understandable as four submodules with specific actions.
- The user can infer what each Runtime action refreshes or syncs.
- Existing runtime safety rules remain true: no secrets rendered, hosted/local
  coexistence, fixed slots, chat pool with one default, global defaults plus
  project overrides.
- Main content and sidebar agree on the selected module and submodule.
