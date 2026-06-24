# Design M32 frontend polish plan

## Context

The app already has backend contracts for the product path:

- Projects and sources are public authoring surfaces.
- Ingestion jobs can be enqueued, inspected, run and retried.
- First-run and v1 quality gate prove a local path to cited chat.
- Chat supports non-streaming, streaming fallback, history and observability.
- Advanced retrieval modes exist as opt-in/evaluable capabilities, but M31
  preserved `dense` as the default.

M32 should make those pieces feel like one local product instead of a set of
separate contract demos.

## Product Surface Inventory

M32 implementation slices should cover these existing workflows:

1. **Product shell.** Compact app shell, project context, navigation between
   authoring, ingestion, chat, history and observability.
2. **Project/source authoring.** Create/select projects, add supported sources,
   review source metadata and preserve form state on failure.
3. **Ingestion operations.** Enqueue, list, inspect, run next and retry jobs
   with visible queued/running/succeeded/blocked/dead-letter states.
4. **First-run guidance.** Give a clear local path from empty app state to
   cited chat using `adaptive-rag first-run smoke` or public authoring and
   ingestion controls.
5. **Chat and retrieval.** Default to `dense`, preserve streaming fallback,
   show citations/tool calls and keep advanced modes out of the default path.
6. **History and observability.** Keep read-only inspection useful without
   exposing secrets, prompts or raw provider payloads.

## Interface Principles

- The first screen is the product workspace, not a marketing landing page.
- UI density should favor repeated local work: compact controls, stable
  dimensions and scannable state.
- Empty, loading, success and error states are part of the feature contract, not
  decoration.
- Failed requests preserve valid user input.
- Long-running ingestion and streaming chat must expose progress/cancel/failure
  states without inventing successful output.
- Browser configuration uses public frontend variables only; no provider keys
  or secrets belong in the browser.

## Retrieval Mode Policy

`dense` remains the default in M32. The frontend should not expose
`contextual_dense`, `lexical`, `hybrid_rrf`, `dense_sparse`, `dense_rerank` or
`graph` as default controls.

If a later implementation slice chooses to show any advanced mode, it must:

- Be opt-in and clearly experimental.
- Reflect the M31 decision row for that strategy.
- Avoid hiding required setup such as sparse backfill or graph live ops.
- Preserve citations, filters and history/audit metadata.

## QA Criteria

Each implementation slice should include:

- Unit/component coverage for request, response and state transitions when the
  project already has suitable frontend test infrastructure.
- API-client coverage for public contract shapes and error preservation.
- Responsive visual QA for desktop and mobile viewports before claiming polish
  complete.
- Console-error and text-overlap checks for the affected screens.
- Documentation updates when the user-facing first-run or local dev path
  changes.

## Sequencing

1. `m32-frontend-polish-plan`: this PR, planning and OpenSpec only.
2. `m32-product-shell-and-authoring`: polish shell, project/source authoring
   and ingestion operations.
3. `m32-chat-retrieval-experience`: polish dense chat, streaming, citations,
   history and read-only observability.
4. `m32-visual-qa-and-docs`: responsive QA, runbook updates and closeout.

## Risks

- UI polish could accidentally add new product scope. Mitigation: M32 consumes
  public contracts only.
- Advanced modes could appear as defaults because they now exist. Mitigation:
  this plan binds frontend exposure to M31 decisions and keeps `dense` default.
- Visual work could pass tests while still being unusable. Mitigation:
  responsive QA, console checks and state inventory are explicit task outputs.
