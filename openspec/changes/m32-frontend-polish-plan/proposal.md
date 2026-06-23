# Proposal M32 frontend polish plan

## Why

M23-M26 made the local-first product flow usable through public surfaces:
project/source authoring, ingestion operations, first-run onboarding and the
v1 quality gate. M28-M31 then stabilized advanced retrieval capabilities and
confirmed that `dense` remains the product default.

The frontend now needs product polish before more backend scope. Without an
explicit plan, UI work can drift into landing pages, decorative redesigns or
advanced retrieval controls that the gate did not promote. M32 opens a bounded
frontend polish track over the existing backend contracts.

## What Changes

- Add the `m32-frontend-polish-plan` OpenSpec change.
- Define the frontend polish inventory: product shell, project/source
  authoring, ingestion ops, first-run guidance, dense retrieval, chat,
  streaming, citations, history and basic observability.
- Require workflow states for empty, loading, success, error, blocked,
  retryable, cancelled and backend-unavailable paths.
- Keep `dense` as the default retrieval experience.
- Keep `contextual_dense`, `lexical`, `hybrid_rrf`, `dense_sparse`,
  `dense_rerank` and `graph` out of the default UI. Any future exposure must be
  opt-in, experimental and consistent with M31 decisions.
- Update progress and roadmap docs so the next implementation slices start
  from this plan.

## Out of Scope

- No frontend runtime implementation in this PR.
- No new backend endpoints, database schema or retrieval defaults.
- No landing page, marketing redesign or unrelated visual rewrite.
- No default promotion for advanced retrieval modes.
- No hosted auth, PDF/Office ingestion, voice, MCP server or multi-user scope.

## Validation

- OpenSpec validation for the new change.
- Full canonical spec validation.
- Markdown/diff hygiene checks.
