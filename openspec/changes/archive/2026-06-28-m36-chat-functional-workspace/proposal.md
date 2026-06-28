# Proposal M36 functional chat workspace

## Why

The current frontend already exposes chat, streaming, history, citations and
observability, but those capabilities are split across panels. The user needs a
more ambitious chat workspace where each surface is
functional, backed by public contracts and verified before the next feature is
started.

The key product gap is not another visual polish pass. It is making the stored
chat audit trail usable during investigation: sessions, messages, tool calls,
retrieval runs, retrieved chunks, citations, provider usage and cost should be
easy to navigate from the chat screen.

## What Changes

- Add a functional chat workspace track over existing public API contracts.
- Promote session history into a left navigation surface with real status
  filters and no fake archive state.
- Add a context panel that summarizes selected-session and project-level usage,
  cost, tokens, latency and models from `provider_usage` and observability.
- Add a conversation minimap based on persisted chat messages.
- Add an action stepper based on persisted tool calls, retrieval runs,
  retrieved chunks and provider usage records.
- Add a source/citation viewer that can inspect source metadata through the
  existing public source API when citation metadata includes a source id.
- Add an STT control only when it is backed by a real contract. Qwen-backed STT
  requires current provider documentation and a backend contract; browser speech
  recognition may be used as a progressive fallback.
- Add a global Settings / Appearance module, following the app-wide theme pattern,
  so Light, Dark and Purple palettes apply across every workspace tab instead
  of being scoped to chat.
- Defer memory or archive features unless this change adds a minimal durable
  contract and verifies it.

## Out of Scope

- No fake archived-session UI if the backend has no archived-session contract.
- No fake memory UI if there is no durable storage or verified source of
  preferences.
- No promotion of advanced retrieval modes into the default chat path.
- No multi-user auth, hosted deployment, PDF/Office ingestion or MCP server.
- No provider secrets in the browser.

## Validation

- Feature-by-feature TDD: each feature starts with failing tests.
- Targeted frontend tests after each feature.
- Full frontend `test`, `typecheck`, `lint` and `build` before finalization.
- OpenSpec strict validation.
- Browser QA for affected chat workspace views on desktop and mobile.
- Browser QA for each workspace tab under every selectable global theme.
- `git diff --check` before commit/PR.
