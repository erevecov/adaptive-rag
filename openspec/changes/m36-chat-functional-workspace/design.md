# Design M36 functional chat workspace

## Context

The repository has durable chat audit tables and public read surfaces for chat
sessions, session detail and observability. The frontend client already knows
these shapes:

- `GET /projects/{project_id}/chat/sessions`
- `GET /projects/{project_id}/chat/sessions/{session_id}`
- `GET /projects/{project_id}/chat/observability/summary`
- `GET /projects/{project_id}/sources/{source_id}`
- `POST /projects/{project_id}/chat` and streaming fallback

M36 should make those contracts feel like one chat investigation workspace.
Where a desired workspace feature lacks a backend contract, the UI must say
so or leave the feature out instead of simulating it.

## Feature Slices

### 1. Session Navigation

Replace the small recent-history panel with a left-side session navigation
surface. It uses `listChatSessions` with public `status`, `limit` and `cursor`
parameters. Tabs should map to real status filters such as all, running,
succeeded and failed. Archive state is not shown unless a public archive
contract exists.

### 2. Context and Usage Panel

Add a right-side context panel for the selected session. It derives session
messages, model config, prompt version, provider usage count, cost, token counts
and latency from `ChatSessionDetailResponse`. Project-level cards can consume
`ChatObservabilitySummary` when loaded. Missing provider values stay visible as
unknown, not invented.

### 3. Conversation Minimap

Render a compact minimap from persisted session messages. Each item navigates to
the corresponding message region in the detail panel. When no session is
selected, the minimap shows an empty state.

### 4. Internal Action Stepper

Render an ordered stepper from stored `tool_calls`, `retrieval_runs`,
`retrieved_chunks` and `provider_usage`. Each step displays status, latency,
cost/tokens when present and links to retrieved chunks or provider records. It
must remain read-only and must not replay providers or retrieval.

### 5. Source and Citation Viewer

Clicking a response citation or retrieved chunk opens a source viewer. If the
citation contains `source_id`, the frontend calls `getSource(projectId,
sourceId)` and renders source metadata, tags and content metadata. If the
source lookup fails, the citation metadata remains visible and the error is
shown without clearing the chat or selected session.

### 6. Speech-to-Text

Qwen-backed STT is only implemented after checking current Qwen/DashScope
documentation and adding a backend contract with tests. If that cannot be
completed in this change, add a browser `SpeechRecognition` fallback as a
progressive enhancement with unsupported/error states, and document Qwen STT as
deferred. The fallback writes transcribed text into the question field and never
sends audio or secrets through the browser.

### 7. Memory

Memory is implemented only if this change adds a minimal durable contract or
can safely reuse an existing verified preference source. Otherwise it remains
deferred in docs. The UI must not present fake memory.

Current repo verification found no durable memory/preference table, repository or
API route. M36 therefore defers memory and keeps the chat UI free of memory
state until a backend contract exists.

## Data Flow

1. User chooses a project id.
2. Session navigation calls `listChatSessions` with the chosen status filter.
3. Selecting a session calls `getChatSession`.
4. The main detail, minimap, action stepper and context panel all render from
   the same `ChatSessionDetailResponse`.
5. Context summary optionally calls `getChatObservabilitySummary` with the same
   project id and public filters.
6. Source viewer calls `getSource` only when the citation has a source id.

## Error Handling

- Missing project id blocks requests with a local validation message.
- History, detail, observability and source viewer errors are isolated.
- Loading, empty and failed states are visible for each panel.
- Long ids and source paths wrap without layout overflow.
- Missing cost, token and latency values are displayed as unknown.

## Testing Strategy

- Start each slice with failing frontend tests in `frontend/src/App.test.tsx`.
- Use `ApiClient` stubs to verify real API method calls and payloads.
- Cover loading, empty and error states for new panels.
- Run targeted tests after each slice.
- Run full frontend test/typecheck/lint/build and OpenSpec validation before
  completion.
- Run browser QA for desktop and mobile chat workspace layouts.
