# Beautiful UI pattern catalog

These are original Adaptive RAG implementations inspired by the publicly inspectable
patterns at [Beautiful UI](https://beautiful-ui-five.vercel.app/). They are not
literal stored copies of the source demos. The catalog is presentational: it does
not fetch, persist, inspect authorization, or invent product outcomes.

Source inspected: 2026-08-11. Eighteen patterns have direct production consumers.
`SelectionToolbar` remains reserved until a supported text-selection action
exists. Consumer paths below record direct production mounts only; tests,
catalog-internal composition and indirect consumers are not counted.

| Source URL | Original pattern name | Internal component | Removed demo dependency / local replacement | Adoption state | Direct production consumer files |
| --- | --- | --- | --- | --- | --- |
| https://beautiful-ui-five.vercel.app/ | Loading State | `LoadingGrid` | None | `adapted-adopted` | `frontend/src/features/authoring/AuthoringView.tsx`<br>`frontend/src/features/history/HistoryInspectorView.tsx`<br>`frontend/src/features/observability/ObservabilityView.tsx`<br>`frontend/src/features/retrieval/RetrievalPlaygroundView.tsx`<br>`frontend/src/features/runtime/RuntimeSettingsView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Thinking | `ReasoningTrace` | None | `adapted-adopted` | `frontend/src/components/ChatPipelineSteps.tsx`<br>`frontend/src/features/history/HistoryInspectorView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Streaming Text | `StreamingAnswer` | None | `adapted-adopted` | `frontend/src/features/chat/ChatWorkspaceView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Approval Card | `ApprovalPrompt` | None | `adapted-adopted` | `frontend/src/features/authoring/AuthoringView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Tool Chips | `ToolActivity` | None | `adapted-adopted` | `frontend/src/features/chat/ChatWorkspaceView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Task Rows | `AgentTaskList` | None | `adapted-adopted` | `frontend/src/features/authoring/AuthoringView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Chat | `ChatSurface` | None | `adapted-adopted` | `frontend/src/features/chat/ChatWorkspaceView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Prompt Bar | `PromptComposer` | `glimm`; local textarea and existing UI primitives | `adapted-adopted` | `frontend/src/features/chat/ChatWorkspaceView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Recommendation Card | `RecommendationPanel` | None | `adapted-adopted` | `frontend/src/features/authoring/AuthoringView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Context Cards | `ContextChunkList` | None | `adapted-adopted` | `frontend/src/features/chat/ChatWorkspaceView.tsx`<br>`frontend/src/features/history/HistoryInspectorView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Diff Table | `ChangeTable` | None | `adapted-adopted` | `frontend/src/features/authoring/AuthoringView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Records Table | `RecordsGrid` | None | `adapted-adopted` | `frontend/src/features/authoring/AuthoringView.tsx`<br>`frontend/src/features/history/HistoryInspectorView.tsx`<br>`frontend/src/features/observability/ObservabilityView.tsx`<br>`frontend/src/features/runtime/RuntimeSettingsView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Filter Table | `FilteredTaskTable` | None | `adapted-adopted` | `frontend/src/features/authoring/AuthoringView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Sidebar Nav | `WorkspaceNavigation` | None | `adapted-adopted` | `frontend/src/features/shell/AppShell.tsx` |
| https://beautiful-ui-five.vercel.app/ | Search | `CommandSearch` | None | `adapted-adopted` | `frontend/src/features/authoring/AuthoringView.tsx`<br>`frontend/src/features/history/HistoryInspectorView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Insight Cards | `InsightDeck` | `liveline`; dependency-free accessible SVG from caller data | `adapted-adopted` | `frontend/src/features/observability/ObservabilityView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Code Block | `CodeStream` | None | `adapted-adopted` | `frontend/src/components/MarkdownAnswer.tsx` |
| https://beautiful-ui-five.vercel.app/ | Fine-tune Card | `ParameterTuner` | None | `adapted-adopted` | `frontend/src/features/runtime/RuntimeSettingsView.tsx` |
| https://beautiful-ui-five.vercel.app/ | Selection Actions | `SelectionToolbar` | Private source-site atoms; existing button primitives | `adapted-reserved` | — |
