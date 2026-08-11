# Beautiful UI Square Frontend Redesign

## Goal

Rebuild the 19 public, copyable patterns shown at
`https://beautiful-ui-five.vercel.app/` as an internal, production-ready React
component library, then redesign the Adaptive RAG frontend with those patterns
where they match an existing product behavior.

The result must extend the square Grok Build visual direction already used by
chat to the entire frontend. It must not paste the site's demos literally,
retain their fictional data, or add interactions unsupported by the product.

## Approved Direction

Use an adapted component library plus a semantic migration of the existing
frontend.

- Reconstruct every catalog pattern as a typed component owned by this repo.
- Keep the components presentational and controlled through props.
- Apply a component only when the current product has a matching behavior.
- Keep an unused component exported and tested for future work rather than
  attaching it to an unrelated screen.
- Preserve current routes, API contracts, authorization, state ownership and
  mutations.
- Do not retain verbatim demo copies in a reference folder.
- Document the source, adaptation and adoption status in the component catalog.

## Source Inventory

The source site exposes 19 components with visible code and copy controls:

1. Loading State
2. Thinking
3. Streaming Text
4. Approval Card
5. Tool Chips
6. Task Rows
7. Chat
8. Prompt Bar
9. Recommendation Card
10. Context Cards
11. Diff Table
12. Records Table
13. Filter Table
14. Sidebar Nav
15. Search
16. Insight Cards
17. Code Block
18. Fine-tune Card
19. Selection Actions

The copied examples are demos, not production APIs. Most are self-contained
React components, but Prompt Bar imports `glimm`, Insight Cards imports
`liveline`, and Selection Actions imports private atoms unavailable in this
repository. The redesign will reproduce the relevant behavior with React,
CSS, SVG, Lucide and the dependencies already installed in the frontend. It
will not add those external or private dependencies.

## Architecture

### Foundation layer

`frontend/src/components/ui/` remains the shared foundation for buttons,
inputs, textareas, selects, panels, badges, lists, tables, tabs, navigation,
menus, popovers and feedback.

The foundation will absorb the global square visual contract so feature code
does not repeat radius, border, elevation and focus classes. Existing primitive
APIs stay compatible unless a new optional variant is necessary for a proven
consumer.

### Pattern layer

Create `frontend/src/components/beautiful-ui/` for the 19 adapted patterns.
Each pattern has one clear purpose, a typed public interface and a `data-slot`
contract for tests and scoped styling. A barrel file exports the public catalog.

These components compose `components/ui` primitives instead of duplicating
button, focus, menu, table or form behavior. They may contain local animation or
layout logic when that behavior belongs to the pattern, but they do not fetch
data or own product mutations.

### Feature layer

Existing views continue to own API requests, domain state, validation,
permissions and side effects. Feature components translate current domain data
into the pattern component props and handle emitted callbacks.

No Beautiful UI demo nouns, hard-coded records, pretend metrics or simulated
agent steps may appear in production feature code.

## Component Catalog And Adoption

| Internal component | Responsibility | Current adoption |
| --- | --- | --- |
| `LoadingGrid` | Compact, reduced-motion-safe loading indicator with optional elapsed time | Chat, session history, sources, retrieval, observability and runtime loading states |
| `ReasoningTrace` | Collapsible ordered reasoning or execution steps | `ChatPipelineSteps` and the inspector action stepper |
| `StreamingAnswer` | Progressive answer container with sources and response actions | Live and completed chat responses |
| `ApprovalPrompt` | Human approval question with bounded choices and custom input | Knowledge proposal approve, reject and refine flows |
| `ToolActivity` | Collapsible tool calls, results and affected artifacts | Chat tool-call details and response details |
| `AgentTaskList` | Running, failed and completed task rows with expandable details | Ingestion jobs and observable background work |
| `ChatSurface` | Transcript and response composition shell | Chat workspace without replacing its state or streaming logic |
| `PromptComposer` | Multiline prompt, attachments, dictation, send and cancel controls | Existing chat composer |
| `RecommendationPanel` | Actionable recommendation, confidence and alternatives | Existing knowledge proposals and actionable drafts only |
| `ContextChunkList` | Retrieved chunks with source, score and metadata | Chat citations, retrieval results, context inspector and source viewer |
| `ChangeTable` | Original-versus-proposed structured changes | Knowledge proposal comparison and refinement review |
| `RecordsGrid` | Sortable, selectable, horizontally safe record table | Workspaces, users, sources, provider connections and models where tabular presentation is clearer than cards |
| `FilteredTaskTable` | Status filters plus data-dense task rows | Ingestion and observability task views |
| `WorkspaceNavigation` | Workspace switcher, primary navigation and contextual sections | App sidebar and session navigation composition |
| `CommandSearch` | Accessible filtering/search surface with empty state | Session, workspace, source and other long record lists |
| `InsightDeck` | Paged operational findings and compact trend evidence | Observability summary using real metrics only |
| `CodeStream` | Accessible code block with language, line display and copy action | Markdown code fences and tool outputs |
| `ParameterTuner` | Labelled numeric and enumerated controls with value feedback | Retrieval and runtime settings that already expose tunable parameters |
| `SelectionToolbar` | Actions anchored to a selected text range | Exported and tested, but not integrated until a real supported text-selection action exists |

All 19 components will exist in the library. Adoption is conditional: a feature
must already provide the underlying semantics and callback before the component
is mounted there.

## Visual Contract

### Shape

- Use a global `2px` radius for panels, controls, menus, tables, chips, cards
  and overlays.
- Remove the chat-only `data-chat-radius="square"` probe after the global
  contract replaces it.
- `rounded-full` is reserved for genuinely circular content such as avatars,
  status dots, radio indicators and circular progress marks.
- Prefer flat surfaces, hairline borders and background shifts over elevation.
- Keep shadows only where an overlay requires separation from the page.

### Color and themes

- Preserve Light, Dark and Purple.
- Use the current semantic tokens rather than copying the source site's palette.
- Add new semantic tokens only when a pattern cannot be expressed with the
  current background, foreground, card, muted, accent, border, ring,
  destructive and status tokens.
- Do not add feature-local hard-coded colors for normal UI state.

### Density and typography

- Keep the product-console density established by chat.
- Preserve readable minimum text sizes and 44px touch targets on narrow mobile
  viewports even when visual chrome is compact.
- Prefer tabular numerals for metrics, durations, costs and counts.
- Avoid marketing-scale headings or decorative gradients.

### Motion

- Use motion only for state change, progress, expansion and streamed content.
- Respect `prefers-reduced-motion` for every new animation.
- Timers used by visual components must be optional or disabled when the caller
  supplies a terminal state.

## Data Flow

1. A feature view receives or owns current domain data.
2. The view derives the typed presentation model expected by a catalog
   component.
3. The catalog component renders state and emits semantic callbacks.
4. The feature view performs the existing request, mutation or navigation.
5. Updated domain state returns through props.

The pattern layer must not import `ApiClient`, call `fetch`, persist domain
records, inspect authorization, or invent optimistic success.

## Loading, Empty, Error And Durable States

- `LoadingGrid` represents active loading only; it must not replace error or
  empty states.
- Existing `InlineFeedback`, `Callout` and `EmptyState` semantics remain the
  source for errors, warnings and durable contextual feedback.
- A failed action remains visible in the feature that owns it and does not turn
  into a transient animation-only result.
- Components must expose disabled and busy states without layout shift.
- Missing optional data renders an explicit unknown or empty value rather than
  a fabricated metric.

## Accessibility

- Preserve or improve existing accessible names, roles and labelled controls.
- All interactive components must be operable by keyboard.
- Focus remains visible in all three themes.
- Collapsible controls expose `aria-expanded` and link to the controlled region
  where practical.
- Data tables keep real table semantics and provide an accessible description
  when horizontal scrolling is required.
- Live progress uses polite announcements; destructive and blocking errors use
  alert semantics.
- Overlays retain focus trapping, Escape handling and focus restoration.

## Responsive Behavior

- Validate the existing desktop layout and the `680px` mobile breakpoint.
- The sidebar remains an overlay on mobile and must not cover unreachable
  controls.
- Chat keeps one transcript scroller and a pinned composer.
- Tables may scroll horizontally without forcing the page width.
- Inspector overlays and menus remain within the viewport.
- Dense controls must preserve touch targets even with square chrome.

## Migration Sequence

1. Add the global square tokens and adapt the shared UI primitives.
2. Add the 19 pattern components, catalog exports, provenance/adoption
   documentation and focused tests.
3. Migrate shell and navigation.
4. Migrate chat, response details, composer and context inspector.
5. Migrate authoring and retrieval surfaces.
6. Migrate observability and runtime surfaces.
7. Remove feature-local styling made redundant by the new primitives and
   patterns.
8. Run integrated automated and visual verification.

Implementation may use subagents for non-overlapping feature groups. Shared
tokens, primitive APIs, barrel exports and final integration remain owned by the
primary agent to avoid conflicting contracts.

## Testing Strategy

### Component tests

- Test every new public component through rendered behavior and accessibility.
- Test controlled state, callbacks, loading, empty, error, disabled and reduced
  motion behavior where applicable.
- Prefer accessible queries and `data-slot` checks over large snapshots.
- Verify the new square primitive classes and semantic token usage.

### Feature tests

- Update existing view tests to prove current user flows still call the same
  callbacks and API client methods.
- Cover chat send/cancel, attachments, streaming steps, source opening,
  proposal decisions, filtering, sorting, runtime saves and destructive
  confirmations.
- Add discriminating tests that fail if a feature reintroduces raw controls or
  bypasses the intended shared pattern where the migration requires it.

### Integrated verification

- Run frontend unit tests, lint, typecheck and production build.
- Run the relevant repository-wide checks required by the current branch.
- Review the app visually in Light, Dark and Purple at desktop and mobile
  widths.
- Exercise loading, empty, error and populated states where fixtures allow.
- Verify overlays, menus, focus restoration, scroll containers, the chat
  transcript, pinned composer and wide tables.

## Provenance

Create `frontend/src/components/beautiful-ui/README.md` during implementation.
It records:

- the source URL;
- the 19 source pattern names;
- each internal component name;
- whether the component is adapted and adopted, or adapted and reserved;
- removed demo dependencies and the local replacement approach;
- the date the source was inspected.

The repository stores only the adapted implementation, not a verbatim archive
of the public demos.

## Non-Goals

- No backend, database, API or authorization changes.
- No new application routes solely to showcase components.
- No Storybook or parallel demo application.
- No copied fictional records, flavors, providers or metrics.
- No `glimm`, `liveline` or unavailable private source-site atoms.
- No speculative AI selection-editing workflow.
- No replacement of current themes.
- No redesign of product information architecture beyond presenting existing
  navigation more consistently.

## Completion Criteria

The work is complete when all 19 adapted components are exported and tested,
every approved current adoption point uses the new pattern without changing
its product behavior, the square visual contract covers the full frontend, all
automated verification passes, and desktop/mobile visual review succeeds in
Light, Dark and Purple.
