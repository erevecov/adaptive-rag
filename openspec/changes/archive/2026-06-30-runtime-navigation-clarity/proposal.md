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
