# Beautiful UI pattern catalog

These are original Adaptive RAG implementations inspired by the publicly inspectable
patterns at [Beautiful UI](https://beautiful-ui-five.vercel.app/). They are not
literal stored copies of the source demos. The catalog is presentational: it does
not fetch, persist, inspect authorization, or invent product outcomes.

Source inspected: 2026-08-11. All patterns below are adapted but not yet adopted
by a feature at this catalog milestone. `SelectionToolbar` is reserved until a
supported text-selection action exists.

| Source URL | Original pattern name | Internal component | Removed demo dependency / local replacement | Adoption state |
| --- | --- | --- | --- | --- |
| https://beautiful-ui-five.vercel.app/ | Loading State | `LoadingGrid` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Thinking | `ReasoningTrace` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Streaming Text | `StreamingAnswer` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Approval Card | `ApprovalPrompt` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Tool Chips | `ToolActivity` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Task Rows | `AgentTaskList` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Chat | `ChatSurface` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Prompt Bar | `PromptComposer` | `glimm`; local textarea and existing UI primitives | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Recommendation Card | `RecommendationPanel` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Context Cards | `ContextChunkList` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Diff Table | `ChangeTable` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Records Table | `RecordsGrid` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Filter Table | `FilteredTaskTable` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Sidebar Nav | `WorkspaceNavigation` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Search | `CommandSearch` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Insight Cards | `InsightDeck` | `liveline`; dependency-free accessible SVG from caller data | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Code Block | `CodeStream` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Fine-tune Card | `ParameterTuner` | None | `adapted-planned` |
| https://beautiful-ui-five.vercel.app/ | Selection Actions | `SelectionToolbar` | Private source-site atoms; existing button primitives | `adapted-reserved` |

No feature adoption is claimed in this document. A later feature task may promote
an entry to `adapted-adopted` only after it has a real consumer with matching
product semantics.
