# Chat Stepper Live Events Design

## Decision

Implement the BeFlow-style chat stepper as a real backend/frontend contract, not
as a frontend-only animation. The selected direction is:

- emit live `step` SSE events from `ChatService.stream`;
- persist the completed step snapshot on the assistant message metadata;
- render the same step tree during streaming and after session reload;
- persist the user's expanded/collapsed preference in browser `localStorage`.

This opens a new OpenSpec slice because it expands `chat-streaming`,
`chat-frontend` and the durable chat history metadata contract.

## Goals

- Show in-progress chat internals while an answer is running, matching the
  BeFlow pattern: compact ticker when collapsed, expanded tree when open.
- Let each step expose finer detail such as model, token counts, estimated
  cost, latency, result counts and errors when available.
- Keep finished answers compact under one `details` control that includes
  steps, model/usage context and sources.
- Rehydrate the exact completed step tree from persisted history when the user
  selects or reloads a chat session.
- Preserve existing non-streaming and streaming clients by keeping the current
  `final` payload compatible.

## Non-Goals

- No new retrieval strategy or ranking default.
- No WebSocket contract.
- No replay, edit or rerun behavior.
- No synthetic success state when backend data is missing.
- No attempt to make provider costs perfect when provider usage is absent; the
  UI must render unknown cost/tokens explicitly.

## Backend Contract

Extend `ChatStreamEventName` with `step`. The event payload uses a stable public
shape inspired by BeFlow:

```json
{
  "id": "retrieval",
  "status": "start",
  "elapsed_ms": 14400,
  "detail": {
    "hits": 30,
    "fused": 30,
    "error": "optional stable error"
  },
  "usage": {
    "slot": "chat",
    "model": "qwen-plus",
    "provider": "qwen",
    "input_tokens": 1200,
    "output_tokens": 240,
    "total_tokens": 1440,
    "estimated_cost_usd": 0.0042,
    "cost_source": "computed"
  }
}
```

`status=start` starts or appends a running step. `status=done|error` completes
the most recent running step with the same `id`. Repeated tool-like steps are
allowed; singleton phase steps ignore duplicate starts defensively.

Initial step ids for this repo should be conservative:

- `answer`: wraps `runner.run(...)` and carries chat model usage when available.
- `retrieval`: wraps the retrieval tool call and carries `hits`, strategy and
  latency.
- Optional substeps can be added when the service exposes reliable timing:
  `retrieval.embedding`, `retrieval.sparse`, `retrieval.rerank`, `retrieval.graph`.

The implementation should not invent substep timing by splitting an opaque
method call. If only top-level retrieval timing is reliable in the first slice,
render top-level retrieval plus persisted retrieved chunks in detail.

## Persistence

When the assistant message is recorded, include `metadata_json.steps` with the
completed step array. Each persisted step stores:

- `id`;
- terminal `status` (`done` or `error`);
- optional `elapsed_ms`;
- optional `detail`;
- optional `usage`.

History readers do not need a new endpoint for the first slice because
`ChatHistoryMessage.metadata` already exists. The frontend will parse
`metadata.steps` from the assistant message. Malformed individual steps should
be dropped, not allowed to blank the whole response.

The existing audit tables remain the source for the right-inspector read-only
debug view. The new persisted steps are the source for the response-local
stepper because they preserve live display order and the same semantics the
user saw while streaming.

## Frontend Design

Add a small stepper module rather than growing `App.tsx` further:

- `frontend/src/lib/chatSteps.ts`: step event types, parsing, formatting and
  metadata hydration helpers.
- `frontend/src/lib/stepperPreference.ts`: localStorage helpers using
  `adaptive-rag:chat-stepper-expanded`.
- `frontend/src/components/ChatPipelineSteps.tsx`: renderer for ticker,
  expanded tree and finished `details` tree.

Rendering behavior:

- During `requestState === "loading"`, show the live stepper above the composer
  when the current response has any step or when the turn has started but the
  first step has not arrived.
- Collapsed streaming state shows one row: spinner, current phase label and
  elapsed time.
- Expanded streaming state shows ordered steps with running/done/error icons,
  latency on the right and clickable rows for usage/details.
- Finished responses show one `details` chip such as
  `details - 24 s - 30 sources`; opening it renders the same step tree plus
  current model/usage and citations.
- If a historical assistant message has no `metadata.steps`, keep the current
  legacy rendering so older sessions still show answer, citations and tool
  calls.

The localStorage preference is global per browser. If the user collapses the
live stepper, the next turn starts collapsed. Storage failures are ignored and
the current in-memory state still updates.

## Data Flow

1. User submits chat.
2. Frontend initializes an empty in-memory step array and records a
   `startedAt` timestamp.
3. Backend emits `session_started`, then `step` events as phases start and
   finish.
4. Frontend applies `step` events to the current response.
5. Backend records the assistant message with `metadata_json.steps`.
6. Backend emits existing `final`.
7. Frontend replaces final answer/citations as it does today and keeps the
   completed steps on the response.
8. Session detail hydration parses the assistant message metadata and rebuilds
   the same rest-position stepper.

## Error Handling

- If a step errors and the overall stream fails, emit `step` with
  `status=error` before the existing `error` event when possible.
- If provider usage recording fails, do not fail chat; mark cost/tokens unknown
  in the affected step.
- If a stream is canceled client-side, keep the partial in-memory steps but do
  not claim a final persisted answer unless the backend returned one.
- If metadata contains invalid steps, drop only invalid entries and keep the
  rest of the response.

## Testing

Backend tests:

- `chat_stream_step_event` serializes deterministic SSE frames.
- `ChatService.stream` emits ordered `step` events around answer/retrieval work.
- Successful streaming persists assistant `metadata_json.steps`.
- Failed streaming can persist terminal error steps without emitting `final`.
- Existing streaming tests still pass with `final` payload unchanged.

Frontend tests:

- `askChatStream` parses `step` events and invokes a step handler.
- Live response renders collapsed ticker and expanded tree.
- Clicking an LLM/usage step reveals model, tokens and cost.
- Toggle writes and reads `adaptive-rag:chat-stepper-expanded`.
- Session detail rehydrates persisted metadata steps.
- Legacy sessions without steps still render current answer/citation/tool-call
  surfaces.

## Rollout

Implement behind the new contract with no user-facing feature flag. The
frontend remains tolerant of old servers because absence of `step` events falls
back to current streaming status. The backend remains compatible with old
clients because SSE clients that ignore unknown events still process
`answer_delta`, `error` and `final`.
